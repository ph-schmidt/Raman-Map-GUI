"""Top-level package for ramangui.

Exposes the package version as ``__version__``.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ramangui")
except PackageNotFoundError:
    __version__ = "unknown"
