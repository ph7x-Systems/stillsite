"""The `cms` command line: thin wiring from project config to services."""

import http.server
import re
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Annotated, Any, ClassVar

import typer
from cms_build import build_site, create_target, create_theme
from cms_build.builder import Artifact
from cms_core.extensions import ExtensionError
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
    rules = default_ruleset()
    for extension in project.load_extensions():
        rules.extend(extension.validation_rules)  # type: ignore[arg-type]
    ruleset = RuleSet(rules=rules, disabled=set(project.validation_disabled))
    context = ValidationContext(
        required_languages=project.site.languages,
        source_language=project.site.source_language,
        known_categories=(
            tuple(sorted(project.site.categories)) if project.site.categories else None
        ),
    )
    return ruleset.run(content, context)


def _report(report: Report) -> None:
    for result in report.results:
        if result.ok:
            outcome = "pass"
        else:
            outcome = ", ".join(
                part
                for part in (
                    f"{len(result.errors)} error(s)" if result.errors else "",
                    f"{len(result.warnings)} warning(s)" if result.warnings else "",
                )
                if part
            )
        typer.echo(f"{result.rule}: {outcome}")
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
    theme: Annotated[
        str, typer.Option(help="Theme entry point name, e.g. ph7x-reference")
    ] = "default",
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
        data={
            "project_name": name,
            "base_url": base_url,
            "languages": languages,
            "theme": theme,
        },
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
    extensions = project.load_extensions()
    content = project.load_content()
    theme = create_theme(project.site.theme, overrides=project.theme_overrides)
    try:
        comments_provider = project.resolve_comments_provider()
    except ExtensionError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=2) from error
    section_kinds: dict[str, object] = {}
    for extension in sorted(project.load_extensions(), key=lambda e: e.name):
        section_kinds.update(extension.section_kinds)
    artifact = build_site(
        project.site,
        content,
        theme=theme,
        media_files=project.collect_media_files(),
        now=datetime.now(tz=UTC),
        comments_provider=comments_provider,
        section_kinds=section_kinds,  # type: ignore[arg-type]
    )
    # ADR-0028: deterministic post-artifact steps, ordered by extension name.
    for extension in sorted(extensions, key=lambda e: e.name):
        for step in extension.build_steps:
            step(project.site, content, artifact)
    return artifact


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
    target: Annotated[str, typer.Option(help="Deployment target adapter")] = "",
) -> None:
    """Build plus the deployment target's configuration files. Without
    --target, the project's configured ``[build] target`` applies."""
    project = _project(project_dir)
    report = _validate(project)
    if not report.ok:
        _report(report)
        raise typer.Exit(code=1)
    artifact = _build_artifact(project)
    adapter = create_target(target or project.target)
    for path, data in sorted(adapter.extra_files(project.site, artifact).items()):
        artifact.add(path, data)
    written = _write_artifact(artifact, project.output)
    typer.echo(f"exported {written} file(s) for target {adapter.name} into {project.output}")


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    """Static preview that serves the site's own error pages (ADR-0021),
    exactly as the production targets configure their hosts to do — never
    the dev server's bare error page."""

    ERROR_PAGES: ClassVar[dict[int, str]] = {
        401: "401.html",
        403: "403.html",
        404: "404.html",
    }

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        filename = self.ERROR_PAGES.get(code, "50x.html" if code >= 500 else None)
        if filename and self.directory:
            page = Path(self.directory) / filename
            if page.is_file():
                body = page.read_bytes()
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
        super().send_error(code, message, explain)


@app.command()
def demo(
    directory: Annotated[Path, typer.Argument(help="Directory for the demo project")] = Path(
        "sardine-demo"
    ),
    port: Annotated[int, typer.Option(help="Port to serve on")] = 8000,
) -> None:
    """From nothing to a browsable site in one command.

    Scaffolds a demo project, seeds the fictional five-language
    content, builds and serves it — then says what to try next. The
    directory stays afterwards so exploring can continue."""
    if not (directory / PROJECT_FILE).exists():
        from copier import run_copy

        template = Path(__file__).parent / "templates" / "init"
        run_copy(
            str(template),
            str(directory),
            data={
                "project_name": "Sardine Demo",
                "base_url": "https://demo.example",
                "languages": "pt-pt, es, fr, de",
            },
            defaults=True,
            quiet=True,
        )
        typer.echo(f"created {directory / PROJECT_FILE}")
    project = _project(directory)
    with project.open_storage() as storage:
        if not storage.has_content():
            pages, articles, media = seed(storage, project.directory)
            typer.echo(f"seeded {pages} page(s), {articles} article(s) and {media} media asset(s)")
    artifact = _build_artifact(project)
    written = _write_artifact(artifact, project.output)
    typer.echo(f"built {written} file(s) into {project.output}")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  - browse the site below; switch languages in the top navigation")
    typer.echo("  - edit in a browser: pip install sardine-cms-admin, then")
    typer.echo(f"    cms admin create-user me --role admin -p {directory}")
    typer.echo(f"    SARDINE_PROJECT_DIR={directory} SARDINE_ADMIN_COOKIE_SECURE=0 \\")
    typer.echo(f"      SARDINE_STORAGE_URL=sqlite:///{directory}/content.sqlite3 \\")
    typer.echo("      uvicorn --factory cms_admin.app:create_app")
    typer.echo(f"  - the content is portable: cms dump -p {directory}")
    typer.echo("")
    handler = partial(PreviewHandler, directory=str(project.output))
    typer.echo(f"serving the demo at http://127.0.0.1:{port}/ (Ctrl+C to stop)")
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            typer.echo(f"stopped — the demo project stays in {directory}")


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
    handler = partial(PreviewHandler, directory=str(project.output))
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
    language: Annotated[
        str, typer.Option(help="Preferred admin language (en|pt-pt|es|fr|de); default browser")
    ] = "",
    email: Annotated[
        str, typer.Option(help="Optional address for password reset and notifications")
    ] = "",
) -> None:
    """Create an admin account (there are no default credentials)."""
    from datetime import UTC, datetime

    from cms_core.accounts import Role, User
    from cms_core.languages import Language

    try:
        from cms_admin.security import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, hash_password
    except ImportError as error:
        typer.echo("error: the admin package is not installed (pip install cms-admin)", err=True)
        raise typer.Exit(code=2) from error

    try:
        account_role = Role(role)
    except ValueError as error:
        typer.echo(f"error: unknown role {role!r} (editor|reviewer|publisher|admin)", err=True)
        raise typer.Exit(code=2) from error
    account_language: Language | None = None
    if language:
        try:
            account_language = Language(language)
        except ValueError as error:
            typer.echo(f"error: unknown language {language!r} (en|pt-pt|es|fr|de)", err=True)
            raise typer.Exit(code=2) from error
    project = _project(project_dir)
    with project.open_storage() as storage:
        existing = storage.load_user(username)
        if existing is not None and not force:
            typer.echo(f"error: user {username!r} already exists (use --force)", err=True)
            raise typer.Exit(code=3)
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            typer.echo("error: password must contain between 12 and 1024 characters", err=True)
            raise typer.Exit(code=2)
        replacement = User(
            username=username,
            password_hash=hash_password(password),
            role=account_role,
            created_at=datetime.now(UTC),
            language=account_language,
            email=email.strip() or None,
        )
        if existing is not None:
            # Replacing credentials is a security boundary: deleting first
            # revokes every existing session through the database cascade.
            storage.delete_user(username)
        storage.save_user(replacement)
    typer.echo(f"created user {username!r} with role {account_role.value}")


def main() -> None:
    app()


@app.command(
    name="x",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def extension_command(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Extension name (see sardine.toml)")],
    project_dir: ProjectDir = Path(),
) -> None:
    """Run a command an activated extension provides (ADR-0028)."""
    project = _project(project_dir)
    for extension in project.load_extensions():
        if extension.name == name and extension.cli is not None:
            command = typer.main.get_command(extension.cli)  # type: ignore[arg-type]
            command(ctx.args, standalone_mode=True, prog_name=f"cms x {name}")
            return
    typer.echo(f"error: no activated extension named {name!r} provides commands", err=True)
    raise typer.Exit(code=2)


@app.command()
def dump(
    project_dir: ProjectDir = Path(),
    out: Annotated[Path, typer.Option(help="Output directory for the portable dump")] = Path(
        "portable"
    ),
) -> None:
    """Write the portable source of truth: content.json + Markdown tree.

    This is the backup and the migration path — `cms import` reads it
    back losslessly (round-trip verified by the test suite).
    """
    from cms_core.export import export_content_json, export_markdown_files

    project = _project(project_dir)
    content = project.load_content()
    destination = out if out.is_absolute() else project.directory / out
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "content.json").write_text(
        export_content_json(content.articles, content.pages, content.media, content.menu),
        encoding="utf-8",
    )
    for path, body in export_markdown_files(list(content.articles)).items():
        target = destination / "markdown" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    typer.echo(f"dumped {len(content.articles)} article(s) into {destination}")


def _wxr_mapping(authors: list[str], categories: list[str], tags: list[str]) -> Any | None:
    """Parse repeated "source=target" specs into a WxrMapping (ADR-0044)."""
    from cms_core import WxrMapping

    tables: list[dict[str, str]] = []
    for kind, specs, slug_target in (
        ("--map-author", authors, False),
        ("--map-category", categories, True),
        ("--map-tag", tags, True),
    ):
        table: dict[str, str] = {}
        for spec in specs:
            source, separator, target = spec.partition("=")
            if not separator or not source:
                typer.echo(f'error: {kind} takes "source=target" (got {spec!r})', err=True)
                raise typer.Exit(code=2)
            if slug_target and target and not re.fullmatch(r"[a-z0-9-]+", target):
                typer.echo(
                    f"error: {kind} target must be a slug (lowercase, digits, dashes): {target!r}",
                    err=True,
                )
                raise typer.Exit(code=2)
            table[source] = target
        tables.append(table)
    if not any(tables):
        return None
    return WxrMapping(authors=tables[0], categories=tables[1], tags=tables[2])


def _warn_unmatched(mapping: Any, report: Any) -> None:
    """A mapping key absent from this export warns and proceeds (ADR-0044)."""
    for kind, keys, seen in (
        ("--map-author", mapping.authors, report.authors),
        ("--map-category", mapping.categories, report.categories),
        ("--map-tag", mapping.tags, report.tags),
    ):
        for missing in sorted(set(keys) - set(seen)):
            typer.echo(f'warning: {kind} "{missing}" matched nothing in this export')


def _record_wxr_redirects(
    project: Project, articles: list[Any], renamed: list[tuple[Any, Any]]
) -> None:
    """Keep source URLs alive: record redirects from every imported
    post's original path to its address on this site (ADR-0046).

    Deterministic (articles processed in sorted order, table written
    sorted), collision-free (an address that is a live destination
    never becomes a redirect source) and idempotent (a re-run merges
    the same changes into the same map).
    """
    from cms_build.redirects import (
        merge_redirects,
        migration_redirect_changes,
        write_redirects,
    )

    config = project.site
    changes = migration_redirect_changes(config, articles, renamed)
    if not changes:
        return
    existing = dict(config.redirects)
    merged = merge_redirects(existing, changes)
    if merged == existing:
        typer.echo(f"redirects: map already covers {len(changes)} source path(s)")
        return
    write_redirects(project.directory / PROJECT_FILE, merged)
    typer.echo(f"redirects: {len(changes)} source path(s) recorded in [redirects]")


def _fetch_wxr_media(project: Project, storage: Any) -> None:
    """Fetch referenced images into the library and rewrite bodies (ADR-0045)."""
    from cms_core.media_fetch import default_fetcher, fetch_media_for_articles

    migrated = [
        article for article in storage.load_all_articles() if article.fields.get("wxr_post_id")
    ]
    result = fetch_media_for_articles(
        migrated,
        storage.load_all_media_assets(),
        source_language=project.site.source_language,
        fetch=default_fetcher,
    )
    media_root = project.directory / "media"
    for relative, data in sorted(result.files.items()):
        destination = media_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    for asset in result.assets:
        storage.save_media_asset(asset)
    for article in result.articles:
        storage.save_article(article)
    for outcome in result.outcomes:
        if outcome.error is not None:
            typer.echo(f"media: failed {outcome.url}: {outcome.error}")
        elif outcome.reused:
            typer.echo(f"media: reused {outcome.asset_id} for {outcome.url}")
        else:
            typer.echo(f"media: fetched {outcome.url} -> {outcome.asset_id}")
    fetched = sum(1 for o in result.outcomes if o.ok and not o.reused)
    reused = sum(1 for o in result.outcomes if o.reused)
    failed = sum(1 for o in result.outcomes if not o.ok)
    typer.echo(f"media: {fetched} fetched, {reused} reused, {failed} failed")


def _print_wxr_report(report: Any) -> None:
    typer.echo(
        f"WXR 1.2 export: {report.posts} importable post(s) of "
        f"{report.total_items} item(s) — fidelity {report.fidelity:.0f}%"
    )
    typer.echo(f"  authors: {', '.join(report.authors) or '(none)'}")
    typer.echo(f"  categories: {', '.join(report.categories) or '(none)'}")
    typer.echo(f"  tags: {', '.join(report.tags) or '(none)'}")
    typer.echo(f"  referenced media: {len(report.media_urls)} url(s)")
    typer.echo(f"  comments: {report.comments} (not migrated)")
    if report.left_behind:
        typer.echo(f"  left behind: {len(report.left_behind)} item(s)")
        for note in report.left_behind:
            typer.echo(f'    - {note.kind} "{note.title}": {note.reason}')


@app.command(name="import")
def import_command(
    source: Annotated[Path, typer.Argument(help="Portable directory or foreign export file")],
    project_dir: ProjectDir = Path(),
    source_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Input format: portable (cms dump) or wxr (WXR 1.2 blog export)",
        ),
    ] = "portable",
    replace: Annotated[
        bool, typer.Option("--replace", help="Import even if the storage already has content")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report what the export contains without writing (wxr)"),
    ] = False,
    update: Annotated[
        bool,
        typer.Option(
            "--update",
            help="Overwrite entries already migrated from this source (wxr; the entity id is kept)",
        ),
    ] = False,
    fetch_media: Annotated[
        bool,
        typer.Option(
            "--fetch-media",
            help="Download the images imported posts reference into the media library (wxr)",
        ),
    ] = False,
    map_author: Annotated[
        list[str] | None,
        typer.Option(
            "--map-author",
            help='Rename an author at import: "Source=Target"; empty target drops the byline',
        ),
    ] = None,
    map_category: Annotated[
        list[str] | None,
        typer.Option(
            "--map-category",
            help='Rename a category slug at import: "source=target"; empty target drops it',
        ),
    ] = None,
    map_tag: Annotated[
        list[str] | None,
        typer.Option(
            "--map-tag",
            help='Rename a tag slug at import: "source=target"; empty target drops it',
        ),
    ] = None,
) -> None:
    """Import a portable dump or a supported foreign blog export."""
    from cms_core import import_content_json, import_wxr, inspect_wxr

    if source_format not in {"portable", "wxr"}:
        typer.echo(
            f"error: unknown import format {source_format!r} (use portable or wxr)",
            err=True,
        )
        raise typer.Exit(code=2)
    wxr_only = dry_run or update or fetch_media or map_author or map_category or map_tag
    if wxr_only and source_format != "wxr":
        typer.echo(
            "error: --dry-run, --update, --fetch-media and --map-* apply to --format wxr only",
            err=True,
        )
        raise typer.Exit(code=2)
    if dry_run and fetch_media:
        typer.echo("error: --fetch-media writes; it cannot combine with --dry-run", err=True)
        raise typer.Exit(code=2)
    if source_format == "wxr":
        if not source.is_file():
            typer.echo(f"error: {source} not found", err=True)
            raise typer.Exit(code=2)
        mapping = _wxr_mapping(map_author or [], map_category or [], map_tag or [])
        payload = source.read_bytes()
        try:
            report = inspect_wxr(payload)
            imported = import_wxr(payload, mapping=mapping)
        except ValueError as error:
            typer.echo(f"error: {error}", err=True)
            raise typer.Exit(code=2) from error
        if mapping is not None:
            _warn_unmatched(mapping, report)
        if dry_run:
            _print_wxr_report(inspect_wxr(payload, mapping=mapping) if mapping else report)
            return
        project = _project(project_dir)
        with project.open_storage() as storage:
            if storage.has_content() and not replace:
                typer.echo(
                    "error: the project storage already has content (use --replace to upsert)",
                    err=True,
                )
                raise typer.Exit(code=3)
            from cms_core.migration import apply_wxr_import

            applied = apply_wxr_import(storage, imported.articles, update=update)
            if fetch_media:
                _fetch_wxr_media(project, storage)
        _record_wxr_redirects(project, applied.landed, applied.renamed)
        typer.echo(
            f"imported {applied.new} new WXR article(s); "
            f"updated {applied.updated}, left {applied.matched} already-migrated untouched; "
            f"skipped {imported.skipped} unsupported item(s)"
        )
        return
    project = _project(project_dir)

    payload_path = source / "content.json"
    if not payload_path.is_file():
        typer.echo(f"error: {payload_path} not found", err=True)
        raise typer.Exit(code=2)
    markdown_files = (
        {
            str(path.relative_to(source / "markdown")): path.read_text(encoding="utf-8")
            for path in sorted((source / "markdown").rglob("*.md"))
        }
        if (source / "markdown").is_dir()
        else {}
    )
    articles, pages, media, menu = import_content_json(
        payload_path.read_text(encoding="utf-8"), markdown_files
    )
    with project.open_storage() as storage:
        if storage.has_content() and not replace:
            typer.echo(
                "error: the project storage already has content (use --replace to upsert)",
                err=True,
            )
            raise typer.Exit(code=3)
        for article in articles:
            storage.save_article(article)
        for page in pages:
            storage.save_page(page)
        for asset in media:
            storage.save_media_asset(asset)
        for item in menu:
            storage.save_menu_item(item)
    typer.echo(
        f"imported {len(articles)} article(s), {len(pages)} page(s), "
        f"{len(media)} media asset(s), {len(menu)} menu item(s)"
    )


@app.command()
def doctor(project_dir: ProjectDir = Path()) -> None:
    """Diagnose the project: configuration, storage, media, environment.

    Read-only. Exits 1 when any check fails; warnings alone exit 0.
    Content-level problems belong to `cms validate` — doctor covers the
    machinery around the content.
    """
    project = _project(project_dir)
    failures = 0

    def report(name: str, ok: bool, detail: str, *, warn: bool = False) -> None:
        nonlocal failures
        verdict = "ok" if ok else ("warn" if warn else "FAIL")
        if not ok and not warn:
            failures += 1
        typer.echo(f"{name}: {verdict} — {detail}")

    # Configuration
    report("config", True, f"sardine.toml loaded ({project.site.name})")
    try:
        create_theme(project.site.theme, overrides=project.theme_overrides)
        report("theme", True, f"{project.site.theme!r} resolves")
    except Exception as error:
        report("theme", False, str(error))
    try:
        extensions = project.load_extensions()
        report(
            "extensions",
            True,
            f"{len(extensions)} activated" if extensions else "none configured",
        )
        from cms_core.extensions import run_health_check

        for extension in sorted(extensions, key=lambda e: e.name):
            for check in run_health_check(extension):
                report(
                    f"extension {extension.name}: {check.name}",
                    check.ok,
                    check.detail or ("ok" if check.ok else "failed"),
                )
    except ExtensionError as error:
        report("extensions", False, str(error))
    try:
        provider = project.resolve_comments_provider()
        detail = "provider resolves" if provider else "not configured"
        report("comments", True, detail)
    except ExtensionError as error:
        report("comments", False, str(error))
    if project.site.image_widths:
        try:
            import PIL  # noqa: F401

            report("images", True, f"Pillow present for widths {list(project.site.image_widths)}")
        except ImportError:
            report(
                "images",
                False,
                "image_widths configured but Pillow is missing (install sardine-cms-build[images])",
            )

    # Storage
    from cms_core.storage import MIGRATIONS

    try:
        with project.open_storage() as storage:
            version = storage.schema_version()
            expected = len(MIGRATIONS)
            report(
                "storage",
                version == expected,
                f"connected, schema {version}/{expected}",
            )
            articles = len(storage.load_all_articles())
            pages = len(storage.load_all_pages())
            media = storage.load_all_media_assets()
            users = len(storage.list_usernames())
            report(
                "content",
                True,
                f"{articles} article(s), {pages} page(s), "
                f"{len(media)} media asset(s), {users} account(s)",
            )
            # Media files on disk
            missing = [
                asset.path
                for asset in media
                if not (project.directory / "media" / asset.path).is_file()
            ]
            if missing:
                report("media", False, f"{len(missing)} referenced file(s) missing: {missing[:3]}")
            else:
                report("media", True, f"{len(media)} file(s) present")
    except Exception as error:
        report("storage", False, str(error))

    # Environment
    import sys

    report("python", True, sys.version.split()[0])
    from importlib import metadata as _metadata

    versions: dict[str, str] = {}
    for dist in (
        "sardine-cms-core",
        "sardine-cms-validation",
        "sardine-cms-build",
        "sardine-cms-cli",
    ):
        try:
            versions[dist] = _metadata.version(dist)
        except _metadata.PackageNotFoundError:
            versions[dist] = "not installed"
    lockstep = len({v for v in versions.values() if v != "not installed"}) <= 1
    report(
        "packages",
        lockstep,
        ", ".join(f"{name} {version}" for name, version in versions.items()),
        warn=not lockstep,
    )

    if failures:
        typer.echo(f"{failures} check(s) failed", err=True)
        raise typer.Exit(code=1)
    typer.echo("all checks passed")
