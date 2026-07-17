"""End-to-end CLI flow on a temporary project."""

from pathlib import Path

from cms_cli.app import app
from typer.testing import CliRunner

runner = CliRunner()

PROJECT_TOML = """
[site]
name = "Aurora Cartography"
base_url = "https://example.com"
languages = ["pt-pt", "es", "fr", "de"]

[storage]
url = "sqlite:///content.sqlite3"

[build]
output = "_site"
"""


def make_project(tmp_path: Path) -> Path:
    (tmp_path / "stillsite.toml").write_text(PROJECT_TOML, encoding="utf-8")
    return tmp_path


def test_missing_project_file_exits_with_code_2(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "-p", str(tmp_path)])
    assert result.exit_code == 2


def test_seed_validate_build_export_flow(tmp_path: Path) -> None:
    project = make_project(tmp_path)

    seeded = runner.invoke(app, ["seed", "-p", str(project)])
    assert seeded.exit_code == 0, seeded.output

    validated = runner.invoke(app, ["validate", "-p", str(project)])
    assert validated.exit_code == 0, validated.output
    assert "0 error(s)" in validated.output

    built = runner.invoke(app, ["build", "-p", str(project)])
    assert built.exit_code == 0, built.output
    assert (project / "_site" / "index.html").is_file()
    assert (project / "_site" / "pt-pt" / "index.html").is_file()

    exported = runner.invoke(app, ["export", "-p", str(project), "--target", "swa"])
    assert exported.exit_code == 0, exported.output
    assert (project / "_site" / "staticwebapp.config.json").is_file()


def test_build_is_reproducible_via_cli(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner.invoke(app, ["seed", "-p", str(project)])
    first = runner.invoke(app, ["build", "-p", str(project)])
    second = runner.invoke(app, ["build", "-p", str(project)])

    def digest(output: str) -> str:
        return output.rsplit("digest ", 1)[1]

    assert digest(first.output) == digest(second.output)
