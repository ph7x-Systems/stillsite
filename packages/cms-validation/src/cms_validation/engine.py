"""Validation engine: composable, configurable rules over site content.

A rule is any object satisfying the :class:`Rule` protocol; a
:class:`RuleSet` runs the enabled rules and aggregates issues. Publishing is
gated on the absence of ``ERROR`` issues.
"""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

from cms_core import Article, Language, MediaAsset, Page


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


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Configuration a rule may consult; never read from globals."""

    required_languages: tuple[Language, ...]


@runtime_checkable
class Rule(Protocol):
    name: str

    def check(self, content: SiteContent, context: ValidationContext) -> Iterable[Issue]: ...


@dataclass(frozen=True, slots=True)
class Report:
    issues: tuple[Issue, ...]

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
        for rule in self.enabled_rules():
            issues.extend(rule.check(content, context))
        issues.sort(key=lambda issue: (issue.subject, issue.code, issue.language or ""))
        return Report(issues=tuple(issues))
