"""Validation engine: composable, configurable rules over site content.

A rule is any object satisfying the :class:`Rule` protocol; a
:class:`RuleSet` runs the enabled rules and aggregates issues. Publishing is
gated on the absence of ``ERROR`` issues.
"""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

from cms_core import SOURCE_LANGUAGE, Article, Language, MediaAsset, MenuItem, Page


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    severity: Severity
    message: str
    subject: str
    language: Language | None = None

    def __str__(self) -> str:
        scope = f" [{self.language.value}]" if self.language else ""
        return f"{self.severity.value}: {self.code}: {self.subject}{scope}: {self.message}"


@dataclass(frozen=True, slots=True)
class SiteContent:
    """The full content set a validation or build run operates on."""

    articles: Sequence[Article] = ()
    pages: Sequence[Page] = ()
    media: Sequence[MediaAsset] = ()
    menu: Sequence[MenuItem] = ()
    """Explicit navigation items (M6); empty derives the menu from content."""


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Configuration a rule may consult; never read from globals."""

    required_languages: tuple[Language, ...]
    source_language: Language = SOURCE_LANGUAGE
    """The language of every entry's source content (ADR-0034)."""
    known_categories: tuple[str, ...] | None = None
    """None disables the check; a tuple restricts article categories to it."""


@runtime_checkable
class Rule(Protocol):
    name: str
    description: str

    def check(self, content: SiteContent, context: ValidationContext) -> Iterable[Issue]: ...


@dataclass(frozen=True, slots=True)
class RuleResult:
    """The outcome of one rule over the full content set — pass or not."""

    rule: str
    description: str
    issues: tuple[Issue, ...]

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is Severity.WARNING)

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class Report:
    issues: tuple[Issue, ...]
    results: tuple[RuleResult, ...] = ()
    """One entry per rule that ran, passing rules included."""

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is Severity.WARNING)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(slots=True)
class RuleSet:
    rules: list[Rule] = field(default_factory=list)
    disabled: set[str] = field(default_factory=set)

    def enabled_rules(self) -> Iterator[Rule]:
        return (rule for rule in self.rules if rule.name not in self.disabled)

    def run(self, content: SiteContent, context: ValidationContext) -> Report:
        issues: list[Issue] = []
        results: list[RuleResult] = []
        for rule in self.enabled_rules():
            found = tuple(rule.check(content, context))
            results.append(RuleResult(rule=rule.name, description=rule.description, issues=found))
            issues.extend(found)
        issues.sort(key=lambda issue: (issue.subject, issue.code, issue.language or ""))
        return Report(issues=tuple(issues), results=tuple(results))
