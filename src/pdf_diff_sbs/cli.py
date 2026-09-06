"""Command-line entry point."""

import argparse
from pathlib import Path

from . import __version__
from .core import compare, scan


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Create a searchable, side-by-side PDF with word-level changes highlighted."
    )
    parser.add_argument("old", nargs="?", type=Path, help="Earlier PDF")
    parser.add_argument("new", nargs="?", type=Path, help="Revised PDF")
    parser.add_argument("-o", "--output", type=Path, default=Path("output/pdf/diff.pdf"))
    parser.add_argument("--list", action="store_true", help="List PDFs recursively and exit")
    parser.add_argument("--directory", type=Path, default=Path("."),
                        help="Directory to scan or use for automatic v0/current selection")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    if args.list and (args.old is not None or args.new is not None):
        parser.error("--list cannot be combined with OLD or NEW.")
    if bool(args.old) != bool(args.new):
        parser.error("Provide both OLD and NEW, or neither.")
    try:
        if args.list:
            for path in scan(args.directory):
                print(path)
            return 0
        if args.old is None:
            previous = args.directory / "v0"
            pairs = [(p, args.directory / p.name) for p in scan(previous)
                     if p.parent == previous and (args.directory / p.name).is_file()]
            if len(pairs) != 1:
                parser.error("Cannot select a unique v0/current pair. Provide OLD and NEW explicitly.")
            args.old, args.new = pairs[0]
        result = compare(args.old, args.new, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Created {result.output} ({result.pages} pages; "
          f"{result.removed_words} removed, {result.added_words} added words)")
    return 0
