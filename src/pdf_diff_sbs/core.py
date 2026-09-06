#!/usr/bin/env python3
"""Create a searchable, side-by-side PDF with word-level changes highlighted."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

import pymupdf as fitz


@dataclass(frozen=True)
class ComparisonResult:
    """Summary of a completed comparison."""

    output: Path
    pages: int
    removed_words: int
    added_words: int


@dataclass
class Word:
    text: str
    locations: list  # (page number, rectangle, block number, line number)


def scan(root):
    """List input PDFs recursively, excluding output and working directories."""
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    excluded = {".venv", ".git", "output", "tmp", "__pycache__"}
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and p.suffix.lower() == ".pdf"
                  and not excluded.intersection(p.relative_to(root).parts))


def repeated_marginal_lines(document):
    counts = {}
    for page in document:
        seen = set()
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                y0, y1 = line["bbox"][1], line["bbox"][3]
                if y1 < page.rect.height * 0.10 or y0 > page.rect.height * 0.85:
                    seen.add(" ".join("".join(s["text"] for s in line["spans"]).split()))
        for text in seen:
            counts[text] = counts.get(text, 0) + 1
    return {text for text, count in counts.items() if count >= 2}


def words(document, ignored_lines=frozenset()):
    result = []
    for page_number, page in enumerate(document):
        extracted = page.get_text("words", sort=True)
        lines = {}
        for word in extracted:
            lines.setdefault((word[5], word[6]), []).append(word)
        page_number_lines = {
            key for key, line in lines.items()
            if re.fullmatch(r"\s*[-–—]?\s*\d+\s*[-–—]?\s*",
                            " ".join(w[4] for w in line))
            and (max(w[3] for w in line) < page.rect.height * 0.10
                 or min(w[1] for w in line) > page.rect.height * 0.90)
        }
        ignored_keys = {
            key for key, line in lines.items()
            if " ".join(w[4] for w in line) in ignored_lines
            and (max(w[3] for w in line) < page.rect.height * 0.10
                 or min(w[1] for w in line) > page.rect.height * 0.85)
        }
        for word in extracted:
            if (word[5], word[6]) in page_number_lines | ignored_keys:
                continue
            value = unicodedata.normalize("NFKC", word[4]).replace("\u00ad", "")
            location = (page_number, fitz.Rect(word[:4]), word[5], word[6])
            # Join line-wrapped words, retaining both rectangles for highlighting.
            if (result and result[-1].text.endswith("-") and value
                    and value[0].islower()
                    and (result[-1].locations[-1][0],
                         *result[-1].locations[-1][2:]) !=
                        (page_number, word[5], word[6])):
                result[-1].text = result[-1].text[:-1] + value
                result[-1].locations.append(location)
            elif value:
                result.append(Word(value, [location]))
    return result


def highlight(document, tokens, color):
    for token in tokens:
        for page_number, rectangle, *_ in token.locations:
            document[page_number].draw_rect(
                rectangle, color=None, fill=color, fill_opacity=0.24, overlay=True)


def label(page, rectangle, text, size=10, color=(0.15, 0.19, 0.24)):
    # Built-in PDF fonts support Latin-1. Substitute unsupported filename glyphs.
    text = text.encode("latin-1", "replace").decode("latin-1")
    while size >= 5:
        if fitz.get_text_length(text, fontsize=size) <= rectangle.width:
            page.insert_text((rectangle.x0, rectangle.y0 + size), text,
                             fontsize=size, color=color)
            return
        size -= 0.5
    page.insert_textbox(rectangle, text, fontsize=5, color=color)


def compare(old_path, new_path, output="output/pdf/diff.pdf"):
    """Write a text comparison PDF and return counts; never overwrite files."""
    old_path, new_path, output = Path(old_path), Path(new_path), Path(output)
    if output.resolve() in {old_path.resolve(), new_path.resolve()}:
        raise ValueError("The output must not overwrite either input PDF.")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}. Choose another output path.")
    with fitz.open(old_path) as old, fitz.open(new_path) as new:
        for path, document in ((old_path, old), (new_path, new)):
            if document.needs_pass:
                raise ValueError(f"Password-protected PDF: {path}")
            if not document.is_pdf or not len(document):
                raise ValueError(f"Not a nonempty PDF: {path}")
        common_margins = repeated_marginal_lines(old) & repeated_marginal_lines(new)
        before, after = words(old, common_margins), words(new, common_margins)
        if not before or not after:
            raise ValueError("Both PDFs need selectable text. OCR scanned PDFs first.")
        matcher = SequenceMatcher(None, [w.text for w in before],
                                  [w.text for w in after], autojunk=False)
        removed, added = [], []
        for operation, i, j, k, l in matcher.get_opcodes():
            if operation != "equal":
                removed.extend(before[i:j])
                added.extend(after[k:l])
        highlight(old, removed, (1, 0.20, 0.20))
        highlight(new, added, (0.05, 0.80, 0.25))
        width = max(p.rect.width for doc in (old, new) for p in doc)
        height = max(p.rect.height for doc in (old, new) for p in doc)
        margin, gap, header, footer = 20, 20, 75, 30
        count = max(len(old), len(new))
        output.parent.mkdir(parents=True, exist_ok=True)
        with fitz.open() as report:
            for index in range(count):
                page = report.new_page(width=2 * width + 2 * margin + gap,
                                       height=height + header + footer)
                label(page, fitz.Rect(margin, 10, page.rect.width - margin, 30),
                      "PDF text comparison", size=16)
                label(page, fitz.Rect(margin, 32, page.rect.width - margin, 48),
                      f"{len(removed)} removed words (red) | {len(added)} added words (green)"
                      " | Layout and image changes are not compared.")
                for column, (document, path, title) in enumerate(
                        ((old, old_path, "OLD"), (new, new_path, "NEW"))):
                    x = margin + column * (width + gap)
                    label(page, fitz.Rect(x, 54, x + width, 72), f"{title}: {path}")
                    area = fitz.Rect(x, header, x + width, header + height)
                    if index < len(document):
                        # show_pdf_page preserves vector content and selectable text.
                        # Empty source pages have no content stream to import.
                        if document[index].get_contents():
                            page.show_pdf_page(area, document, index)
                    else:
                        label(page, fitz.Rect(x + 20, header + 30, x + width, header + 60),
                              "No corresponding page")
                label(page, fitz.Rect(margin, page.rect.height - 21,
                                      page.rect.width - margin, page.rect.height - 5),
                      f"Page {index + 1} of {count} | Compared across the whole document;"
                      " source pages are shown by page number.", size=9)
            report.set_metadata({"title": "PDF text comparison",
                                 "subject": f"{old_path.name} vs {new_path.name}"})
            report.save(output, garbage=4, deflate=True)
    return ComparisonResult(output, count, len(removed), len(added))
