# pdf-diff-sbs

Compare two PDFs and generate a searchable **side-by-side** (SBS) PDF, with removed
words highlighted in red and added words highlighted in green. Original pages retain
their vector content and selectable text.

## Install

Requires Python 3.10+. Use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pdf-diff-sbs
```

On Windows, activate with `.venv\Scripts\activate` instead.

Install a specific PyPI version with:

```bash
python -m pip install "pdf-diff-sbs==0.1.1"
```

PyMuPDF is installed automatically. No Poppler installation is required.

For the latest development version, install from GitHub (requires Git):

```bash
python -m pip install "git+https://github.com/matplo/pdf-diff-sbs.git"
```

To select a GitHub release, append its tag, for example `.git@v0.1.1`.

## Usage

```bash
pdf-diff-sbs old.pdf new.pdf -o comparison.pdf
pdf-diff-sbs --list
pdf-diff-sbs --list --directory /path/to/documents
pdf-diff-sbs --version
```

With no positional arguments, the tool selects the sole matching PDF filename in
`v0/` and the current directory. Use `--directory` to choose another directory for
this automatic selection. Explicit OLD, NEW, and output paths are always relative
to the current working directory.

The default output is `output/pdf/diff.pdf`. Existing files are protected; use another
output filename for a repeat comparison. Recursive scanning skips `.venv`, `.git`,
`output`, `tmp`, and `__pycache__` directories.

You can also run `python -m pdf_diff_sbs` with the same arguments.

## Python API

```python
from pdf_diff_sbs import compare, scan

pdfs = scan("documents")
result = compare("old.pdf", "new.pdf", "comparison.pdf")
print(result.pages, result.removed_words, result.added_words)
```

Paths can be strings or `pathlib.Path` objects. `compare` returns a
`ComparisonResult` with `output`, `pages`, `removed_words`, and `added_words`.
Invalid inputs raise exceptions; neither input nor existing output files are overwritten.

## What the comparison means

- Text is compared across the whole document to reduce differences caused by wrapping
  and page shifts. Source pages are displayed by page number, so matching text may
  appear on different output pages after reflow.
- Whitespace, common ligature encoding differences, and standalone page numbers near
  page edges are ignored. Repeated marginal lines identical in both PDFs are ignored.
- A line-ending hyphen followed by lowercase text is treated as a split word. This
  heuristic can also join genuine compound words. Punctuation and case changes count.
- Formatting, images, signatures, and graphical changes are not compared. Scanned
  PDFs need OCR first; documents with no selectable text are rejected. Image-only
  pages in mixed documents are displayed, but their changes are not detected.
- Reading order depends on PDF extraction; complex columns may cause extra differences.
  Source annotations and form widgets are not imported into the comparison.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
python -m twine check dist/*
```

Tests generate small synthetic PDFs in temporary directories. The repository contains
the package and tests; input documents and generated comparison PDFs are excluded.

## Releases

See [RELEASING.md](RELEASING.md) for the PyPI Trusted Publisher configuration and
tag-triggered release steps. A manual run of the publishing workflow validates the
release build without uploading to PyPI.
