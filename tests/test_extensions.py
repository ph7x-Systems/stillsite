"""The extension contract (ADR-0028): loading, activation, contributions."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from cms_build.builder import Artifact
from cms_cli.app import app
from cms_core import Extension, ExtensionError, load_extensions
from cms_validation import Issue, Severity, SiteContent
from typer.testing import CliRunner

runner = CliRunner()


class ShoutingTitlesRule:
    """Test rule: titles must not be all caps."""

    name = "no-shouting-titles"
    description = "Article titles are not written in all caps"

    def check(self, content: SiteContent, context: object) -> Iterator[Issue]:
        for article in content.articles:
            title = article.source.title
            if title.isupper() and len(title) > 3:
                yield Issue(
                    code=self.name,
                    severity=Severity.WARNING,
                    message="title is all caps",
                    subject=f"article:{article.id}",
                )


def _mark_artifact(config: object, content: object, artifact: Artifact) -> None:
    artifact.add("extension-mark.txt", "made by the test extension\n")


import typer  # noqa: E402

_cli = typer.Typer()


@_cli.command()
def greet() -> None:
    typer.echo("hello from the extension")


@_cli.command()
def version() -> None:
    typer.echo("testext 1.0")


extension = Extension(
    name="testext",
    validation_rules=(ShoutingTitlesRule(),),
    build_steps=(_mark_artifact,),
    cli=_cli,
    section_kinds={"timeline": ("heading", "moments")},
)


def test_dotted_path_loading_and_errors() -> None:
    loaded = load_extensions(["test_extensions:extension"])
    assert [e.name for e in loaded] == ["testext"]
    with pytest.raises(ExtensionError):
        load_extensions(["definitely.missing:nope"])
    with pytest.raises(ExtensionError):
        load_extensions(["test_extensions:runner"])  # not an Extension


def _project_with_extension(tmp_path: Path) -> Path:
    (tmp_path / "sardine.toml").write_text(
        'extensions = ["test_extensions:extension"]\n'
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    return tmp_path


def test_extension_rules_join_validation(tmp_path: Path) -> None:
    project = _project_with_extension(tmp_path)
    seeded = runner.invoke(app, ["seed", "-p", str(project)])
    assert seeded.exit_code == 0, seeded.output
    validated = runner.invoke(app, ["validate", "-p", str(project)])
    assert "no-shouting-titles: pass" in validated.output


def test_extension_build_steps_shape_the_artifact(tmp_path: Path) -> None:
    project = _project_with_extension(tmp_path)
    runner.invoke(app, ["seed", "-p", str(project)])
    built = runner.invoke(app, ["build", "-p", str(project)])
    assert built.exit_code == 0, built.output
    assert (project / "_site" / "extension-mark.txt").is_file()


def test_cms_x_dispatches_to_the_extension_cli(tmp_path: Path) -> None:
    project = _project_with_extension(tmp_path)
    result = runner.invoke(app, ["x", "testext", "-p", str(project), "greet"])
    assert result.exit_code == 0, result.output
    assert "hello from the extension" in result.output
    missing = runner.invoke(app, ["x", "nope", "-p", str(project)])
    assert missing.exit_code == 2


def test_nothing_activates_without_the_toml_entry(tmp_path: Path) -> None:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    validated = runner.invoke(app, ["seed", "-p", str(tmp_path)])
    assert validated.exit_code == 0
    report = runner.invoke(app, ["validate", "-p", str(tmp_path)])
    assert "no-shouting-titles" not in report.output
