"""End-to-end CLI flow on a temporary project."""

from pathlib import Path

from cms_cli.app import app
from cms_cli.project import load_project
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
    (tmp_path / "sardine.toml").write_text(PROJECT_TOML, encoding="utf-8")
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
    # Every rule reports its outcome, passing rules included; the seeded
    # review article keeps a live warning without blocking anything.
    assert "unique-slugs: pass" in validated.output
    assert "required-translations:" in validated.output
    assert "warning" in validated.output

    built = runner.invoke(app, ["build", "-p", str(project)])
    assert built.exit_code == 0, built.output
    assert (project / "_site" / "index.html").is_file()
    assert (project / "_site" / "pt-pt" / "index.html").is_file()

    exported = runner.invoke(app, ["export", "-p", str(project), "--target", "swa"])
    assert exported.exit_code == 0, exported.output
    assert (project / "_site" / "staticwebapp.config.json").is_file()


def test_init_scaffolds_a_building_project(tmp_path: Path) -> None:
    target = tmp_path / "new-site"
    created = runner.invoke(
        app,
        ["init", str(target), "--name", "Test Site", "--base-url", "https://test.example"],
    )
    assert created.exit_code == 0, created.output
    assert (target / "sardine.toml").is_file()
    assert (target / ".copier-answers.yml").is_file()

    runner.invoke(app, ["seed", "-p", str(target)])
    built = runner.invoke(app, ["build", "-p", str(target)])
    assert built.exit_code == 0, built.output
    assert (target / "_site" / "index.html").is_file()

    again = runner.invoke(app, ["init", str(target)])
    assert again.exit_code == 2


def test_seed_refuses_to_overwrite_existing_content(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    first = runner.invoke(app, ["seed", "-p", str(project)])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["seed", "-p", str(project)])
    assert second.exit_code == 3
    assert "--force" in second.output

    forced = runner.invoke(app, ["seed", "-p", str(project), "--force"])
    assert forced.exit_code == 0, forced.output


def test_sqlite_backend_runs_in_wal_mode(tmp_path: Path) -> None:
    import sqlite3

    from cms_core.storage import create_storage

    backend = create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")
    backend.close()
    connection = sqlite3.connect(tmp_path / "cms.sqlite3")
    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    connection.close()


def test_build_is_reproducible_via_cli(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner.invoke(app, ["seed", "-p", str(project)])
    first = runner.invoke(app, ["build", "-p", str(project)])
    second = runner.invoke(app, ["build", "-p", str(project)])

    def digest(output: str) -> str:
        return output.rsplit("digest ", 1)[1]

    assert digest(first.output) == digest(second.output)


def test_admin_create_user_provisions_an_account(tmp_path: Path) -> None:
    runner.invoke(app, ["init", str(tmp_path), "--name", "Demo"])
    result = runner.invoke(
        app,
        ["admin", "create-user", "chef", "-p", str(tmp_path), "--role", "publisher"],
        input="tinned-fish-forever\ntinned-fish-forever\n",
    )
    assert result.exit_code == 0, result.output
    from cms_admin.security import verify_password
    from cms_core.accounts import Role

    project = load_project(tmp_path)
    with project.open_storage() as storage:
        user = storage.load_user("chef")
        assert user is not None
        assert user.role is Role.PUBLISHER
        assert verify_password(user.password_hash, "tinned-fish-forever")
    duplicate = runner.invoke(
        app,
        ["admin", "create-user", "chef", "-p", str(tmp_path), "--role", "editor"],
        input="x\nx\n",
    )
    assert duplicate.exit_code == 3
