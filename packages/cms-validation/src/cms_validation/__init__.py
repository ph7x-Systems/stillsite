"""Configurable content validation rules."""

from cms_validation.engine import (
    Issue,
    Report,
    Rule,
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

__version__ = "0.1.0"

__all__ = [
    "Issue",
    "KnownCategoriesRule",
    "MediaAltCoverageRule",
    "MediaReferencesRule",
    "Report",
    "RequiredTranslationsRule",
    "Rule",
    "RuleSet",
    "Severity",
    "SiteContent",
    "UniqueSlugsRule",
    "ValidationContext",
    "default_ruleset",
]
