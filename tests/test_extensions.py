"""The extension contract (ADR-0028): loading, activation, contributions."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from cms_build.builder import Artifact
from cms_cli.app import app
from cms_core import CommentsProvider, Extension, ExtensionError, load_extensions
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


FISHBOWL_ISLAND = b"customElements.define('site-comments', class extends HTMLElement {});\n"


def _fishbowl_thread_url(base: str, page_url: str) -> str:
    return f"{base.rstrip('/')}/threads?page={page_url}"


extension = Extension(
    name="testext",
    validation_rules=(ShoutingTitlesRule(),),
    build_steps=(_mark_artifact,),
    cli=_cli,
    section_kinds={"timeline": ("heading", "moments")},
    comments_providers={
        "fishbowl": CommentsProvider(island_js=FISHBOWL_ISLAND, thread_url=_fishbowl_thread_url)
    },
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


def _project_with_comments(tmp_path: Path, provider: str) -> Path:
    (tmp_path / "sardine.toml").write_text(
        'extensions = ["test_extensions:extension"]\n'
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n'
        f'[comments]\nprovider = "{provider}"\nurl = "https://discuss.example"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_comments_provider_ships_the_island_and_links_every_article(tmp_path: Path) -> None:
    """ADR-0031: the island is a same-origin artifact asset and every
    article carries the no-JS link to its own thread."""
    project = _project_with_comments(tmp_path, "fishbowl")
    runner.invoke(app, ["seed", "-p", str(project)])
    built = runner.invoke(app, ["build", "-p", str(project)])
    assert built.exit_code == 0, built.output
    island = project / "_site" / "assets" / "comments-island.js"
    assert island.read_bytes() == FISHBOWL_ISLAND
    article_pages = sorted((project / "_site" / "blog").rglob("index.html"))[1:]
    linked = [p for p in article_pages if "https://discuss.example/threads?page=" in p.read_text()]
    assert linked, "no article carries the discussion link"
    html = linked[0].read_text(encoding="utf-8")
    assert "<site-comments" in html
    assert 'type="module" src="/assets/comments-island.js?v=' in html
    # consent-first: the page references no third-party script
    assert 'src="https://' not in html


def test_unknown_comments_provider_fails_the_build_loudly(tmp_path: Path) -> None:
    project = _project_with_comments(tmp_path, "ghost")
    runner.invoke(app, ["seed", "-p", str(project)])
    built = runner.invoke(app, ["build", "-p", str(project)])
    assert built.exit_code == 2
    assert "ghost" in built.output


def test_without_comments_table_the_build_is_unchanged(tmp_path: Path) -> None:
    """No [comments] -> byte-identical output, provider installed or not."""
    (tmp_path / "with").mkdir()
    (tmp_path / "without").mkdir()
    activated = _project_with_extension(tmp_path / "with")
    plain = tmp_path / "without"
    (plain / "sardine.toml").write_text(
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    for project in (activated, plain):
        runner.invoke(app, ["seed", "-p", str(project)])
        built = runner.invoke(app, ["build", "-p", str(project)])
        assert built.exit_code == 0, built.output
    with_files = sorted((activated / "_site").rglob("*"))
    without = plain / "_site"
    for path in with_files:
        if path.name == "extension-mark.txt" or path.is_dir():
            continue
        counterpart = without / path.relative_to(activated / "_site")
        assert counterpart.read_bytes() == path.read_bytes(), path
    assert not (without / "assets" / "comments-island.js").exists()
