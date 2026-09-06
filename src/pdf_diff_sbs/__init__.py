"""Word-level, side-by-side PDF comparison."""

from importlib.metadata import version

from .core import ComparisonResult, compare, scan

__version__ = version("pdf-diff-sbs")
__all__ = ["ComparisonResult", "compare", "scan", "__version__"]
