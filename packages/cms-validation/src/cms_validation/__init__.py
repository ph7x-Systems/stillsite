"""Configurable content validation rules."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from cms_validation.engine import (
    Issue,
    Report,
    Rule,
    RuleResult,
    RuleSet,
    Severity,
    SiteContent,
    ValidationContext,
)
from cms_validation.rules import (
    KnownCategoriesRule,
    MediaAltCoverageRule,
    MediaReferencesRule,
    RequiredTranslationsRule,
    UniqueSlugsRule,
    default_ruleset,
)

try:
    __version__ = _dist_version("sardine-cms-validation")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = [
    "Issue",
    "KnownCategoriesRule",
    "MediaAltCoverageRule",
    "MediaReferencesRule",
    "Report",
    "RequiredTranslationsRule",
    "Rule",
    "RuleResult",
    "RuleSet",
    "Severity",
    "SiteContent",
    "UniqueSlugsRule",
    "ValidationContext",
    "default_ruleset",
]
