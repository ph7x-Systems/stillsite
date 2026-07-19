"""The `cms` command line: thin wiring from project config to services."""

import http.server
from functools import partial
from pathlib import Path
from typing import Annotated

import typer
from cms_build import build_site, create_target, create_theme
from cms_build.builder import Artifact
from cms_validation import Report, RuleSet, ValidationContext, default_ruleset

from cms_cli.project import PROJECT_FILE, Project, load_project
from cms_cli.seed import seed

app = typer.Typer(add_completion=False, no_args_is_help=True)

ProjectDir = Annotated[
    Path,
    typer.Option("--project", "-p", help="Project directory containing sardine.toml"),
]


def _project(directory: Path) -> Project:
    try:
        return load_project(directory.resolve())
    except FileNotFoundError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=2) from error


def _validate(project: Project) -> Report:
    content = project.load_content()
    ruleset = RuleSet(rules=default_ruleset())
    context = ValidationContext(
        required_languages=project.site.languages,
        known_categories=(
            tuple(sorted(project.site.categories)) if project.site.categories else None
        ),
    )
    return ruleset.run(content, context)


def _report(report: Report) -> None:
    for issue in report.issues:
        typer.echo(str(issue))
    typer.echo(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")


def _write_artifact(artifact: Artifact, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    root = output.resolve()
    for path in artifact.paths():
        destination = (root / path).resolve()
        if not destination.is_relative_to(root):
            raise ValueError(f"artifact path escapes the output directory: {path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(artifact.files[path])
    return len(artifact.paths())


@app.command()
def init(
    directory: Annotated[Path, typer.Argument(help="Directory for the new project")],
    name: Annotated[str, typer.Option(help="Site name")] = "My Sardine CMS",
    base_url: Annotated[str, typer.Option(help="Canonical base URL")] = "https://example.com",
    languages: Annotated[
        str, typer.Option(help="Required target languages, comma-separated")
    ] = "pt-pt, es, fr, de",
) -> None:
    """Scaffold a new project from the built-in Copier template."""
    from copier import run_copy

    if (directory / PROJECT_FILE).exists():
        typer.echo(f"error: {directory} already contains {PROJECT_FILE}", err=True)
        raise typer.Exit(code=2)
    template = Path(__file__).parent / "templates" / "init"
    run_copy(
        str(template),
        str(directory),
        data={"project_name": name, "base_url": base_url, "languages": languages},
        defaults=True,
        quiet=True,
    )
    typer.echo(f"created {directory / PROJECT_FILE} — next: cms seed -p {directory}")


@app.command(name="seed")
def seed_command(
    project_dir: ProjectDir = Path(),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite content that already exists")
    ] = False,
) -> None:
    """Create fictional starter content in the project storage."""
    project = _project(project_dir)
    with project.open_storage() as storage:
        if storage.has_content() and not force:
            typer.echo(
                "error: the project storage already has content; "
                "seeding would overwrite it (use --force to do so anyway)",
                err=True,
            )
            raise typer.Exit(code=3)
        pages, articles, media = seed(storage, project.directory)
    typer.echo(f"seeded {pages} page(s), {articles} article(s) and {media} media asset(s)")


@app.command()
def validate(project_dir: ProjectDir = Path()) -> None:
    """Run the validation rules; exits non-zero when errors exist."""
    project = _project(project_dir)
    report = _validate(project)
    _report(report)
    if not report.ok:
        raise typer.Exit(code=1)


def _build_artifact(project: Project) -> Artifact:
    theme = create_theme(project.site.theme, overrides=project.theme_overrides)
    return build_site(
        project.site,
        project.load_content(),
        theme=theme,
        media_files=project.collect_media_files(),
    )


@app.command()
def build(project_dir: ProjectDir = Path()) -> None:
    """Validate, then produce the deterministic static build."""
    project = _project(project_dir)
    report = _validate(project)
    if not report.ok:
        _report(report)
        raise typer.Exit(code=1)
    artifact = _build_artifact(project)
    written = _write_artifact(artifact, project.output)
    typer.echo(f"built {written} file(s) into {project.output} (digest {artifact.digest()[:12]})")


@app.command()
def export(
    project_dir: ProjectDir = Path(),
    target: Annotated[str, typer.Option(help="Deployment target adapter")] = "generic",
) -> None:
    """Build plus the deployment target's configuration files."""
    project = _project(project_dir)
    report = _validate(project)
    if not report.ok:
        _report(report)
        raise typer.Exit(code=1)
    artifact = _build_artifact(project)
    adapter = create_target(target)
    for path, data in sorted(adapter.extra_files(project.site, artifact).items()):
        artifact.add(path, data)
    written = _write_artifact(artifact, project.output)
    typer.echo(f"exported {written} file(s) for target {adapter.name} into {project.output}")


@app.command()
def preview(
    project_dir: ProjectDir = Path(),
    port: Annotated[int, typer.Option(help="Port to serve on")] = 8000,
) -> None:
    """Serve the built site locally (build first)."""
    project = _project(project_dir)
    if not project.output.is_dir():
        typer.echo("error: output directory missing — run `cms build` first", err=True)
        raise typer.Exit(code=2)
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(project.output))
    typer.echo(f"serving {project.output} at http://127.0.0.1:{port}/ (Ctrl+C to stop)")
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        server.serve_forever()


admin_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(admin_app, name="admin", help="Admin panel operations")


@admin_app.command(name="create-user")
def admin_create_user(
    username: Annotated[str, typer.Argument(help="Account username (lowercase)")],
    project_dir: ProjectDir = Path(),
    role: Annotated[str, typer.Option(help="editor | reviewer | publisher | admin")] = "editor",
    password: Annotated[
        str,
        typer.Option(prompt=True, confirmation_prompt=True, hide_input=True, help="Prompted"),
    ] = "",
    force: Annotated[
        bool, typer.Option("--force", help="Replace the account if it already exists")
    ] = False,
) -> None:
    """Create an admin account (there are no default credentials)."""
    from datetime import UTC, datetime

    from cms_core.accounts import Role, User

    try:
        from cms_admin.security import hash_password
    except ImportError as error:
        typer.echo("error: the admin package is not installed (pip install cms-admin)", err=True)
        raise typer.Exit(code=2) from error

    try:
        account_role = Role(role)
    except ValueError as error:
        typer.echo(f"error: unknown role {role!r} (editor|reviewer|publisher|admin)", err=True)
        raise typer.Exit(code=2) from error
    project = _project(project_dir)
    with project.open_storage() as storage:
        if storage.load_user(username) is not None and not force:
            typer.echo(f"error: user {username!r} already exists (use --force)", err=True)
            raise typer.Exit(code=3)
        storage.save_user(
            User(
                username=username,
                password_hash=hash_password(password),
                role=account_role,
                created_at=datetime.now(UTC),
            )
        )
    typer.echo(f"created user {username!r} with role {account_role.value}")


def main() -> None:
    app()
