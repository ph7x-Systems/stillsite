"""Sardine CMS command line interface."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

try:
    __version__ = _dist_version("sardine-cms-cli")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"
