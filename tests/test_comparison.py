"""Exercise the installed package using synthetic PDFs only."""

import hashlib
import subprocess
import sys

import pymupdf as fitz
import pytest

from pdf_diff_sbs import __version__, compare, scan


def make_pdf(path, pages):
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as document:
        for text in pages:
            page = document.new_page()
            if text:
                page.insert_text((60, 100), text)
        document.save(path)
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_replacement_highlights_and_preserves_inputs(tmp_path):
    old = make_pdf(tmp_path / "old.pdf", ["Alpha beta gamma"])
    new = make_pdf(tmp_path / "new.pdf", ["Alpha delta gamma"])
    hashes = digest(old), digest(new)
    result = compare(str(old), str(new), str(tmp_path / "diff.pdf"))
    assert (result.pages, result.removed_words, result.added_words) == (1, 1, 1)
    assert (digest(old), digest(new)) == hashes
    with fitz.open(result.output) as report:
        text = report[0].get_text()
        assert "Alpha beta gamma" in text and "Alpha delta gamma" in text
        fills = [d["fill"] for d in report[0].get_drawings() if d["fill"]]
        assert any(c[0] > .9 and c[1] < .3 for c in fills)
        assert any(c[1] > .7 and c[0] < .1 for c in fills)


def test_reflow_and_hyphenation_across_pages(tmp_path):
    old = make_pdf(tmp_path / "old.pdf", ["Alpha beta gam-\nma delta"])
    new = make_pdf(tmp_path / "new.pdf", ["Alpha beta", "gamma delta epsilon"])
    result = compare(old, new, tmp_path / "diff.pdf")
    assert (result.pages, result.removed_words, result.added_words) == (2, 0, 1)
    with fitz.open(result.output) as report:
        assert "No corresponding page" in report[1].get_text()


def test_identical_and_blank_page(tmp_path):
    source = make_pdf(tmp_path / "source.pdf", ["Same words", ""])
    result = compare(source, source, tmp_path / "diff.pdf")
    assert (result.pages, result.removed_words, result.added_words) == (2, 0, 0)


def test_shared_footers_do_not_interrupt_reflow(tmp_path):
    old = make_pdf(tmp_path / "old.pdf", ["Alpha beta", "gamma delta"])
    new = make_pdf(tmp_path / "new.pdf", ["Alpha", "beta gamma delta"])
    for path in [old, new]:
        with fitz.open(path) as doc:
            for i, page in enumerate(doc):
                page.insert_text((60, 740), "Shared footer")
                page.insert_text((280, 40), f"- {i+1} -")
            doc.saveIncr()
    result = compare(old, new, tmp_path / "diff.pdf")
    assert (result.removed_words, result.added_words) == (0, 0)


def test_overwrites_are_rejected(tmp_path):
    source = make_pdf(tmp_path / "source.pdf", ["Alpha"])
    original = digest(source)
    with pytest.raises(ValueError, match="input PDF"):
        compare(source, source, source)
    existing = tmp_path / "existing.pdf"
    existing.write_bytes(b"Existing file")
    with pytest.raises(FileExistsError):
        compare(source, source, existing)
    assert existing.read_bytes() == b"Existing file"
    assert digest(source) == original


def test_no_text_is_rejected(tmp_path):
    blank = make_pdf(tmp_path / "blank.pdf", [""])
    text = make_pdf(tmp_path / "text.pdf", ["Some words"])
    with pytest.raises(ValueError, match="selectable text"):
        compare(blank, text, tmp_path / "diff.pdf")


def test_scan_nested_case_and_exclusions(tmp_path):
    keep = make_pdf(tmp_path / "nested" / "input.PDF", ["Text"])
    make_pdf(tmp_path / "output" / "diff.pdf", ["Text"])
    make_pdf(tmp_path / ".venv" / "test.pdf", ["Text"])
    assert scan(str(tmp_path)) == [keep]


def run_cli(tmp_path, *args):
    return subprocess.run([sys.executable, "-m", "pdf_diff_sbs", *map(str, args)],
                          cwd=tmp_path, capture_output=True, text=True)


def test_cli_auto_selection_and_output_protection(tmp_path):
    make_pdf(tmp_path / "v0" / "letter.pdf", ["Alpha"])
    make_pdf(tmp_path / "letter.pdf", ["Alpha beta"])
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "0 removed, 1 added" in result.stdout
    result = run_cli(tmp_path)
    assert result.returncode == 1 and "already exists" in result.stderr


def test_cli_bad_input_and_version(tmp_path):
    result = run_cli(tmp_path, "missing.pdf", "also-missing.pdf")
    assert result.returncode != 0 and "Traceback" not in result.stderr
    result = run_cli(tmp_path, "--version")
    assert result.returncode == 0 and __version__ in result.stdout
    result = run_cli(tmp_path, "--list", "--directory", tmp_path / "missing")
    assert result.returncode == 1 and "Not a directory" in result.stderr


def test_cli_ambiguous_auto_selection(tmp_path):
    for name in ["one.pdf", "two.pdf"]:
        make_pdf(tmp_path / "v0" / name, ["Alpha"])
        make_pdf(tmp_path / name, ["Beta"])
    result = run_cli(tmp_path)
    assert result.returncode == 2 and "unique" in result.stderr
