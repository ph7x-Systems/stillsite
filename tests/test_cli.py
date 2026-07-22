"""End-to-end CLI flow on a temporary project."""

from pathlib import Path

import pytest
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


def test_init_writes_the_chosen_theme(tmp_path: Path) -> None:
    """--theme lands in sardine.toml, and omitting it keeps the bare default.

    Without this the README had to tell the reader to open sardine.toml and
    edit it by hand between two blocks of commands, because installing a theme
    package did nothing on its own.
    """
    chosen = tmp_path / "themed"
    assert runner.invoke(app, ["init", str(chosen), "--theme", "ph7x-reference"]).exit_code == 0
    assert 'theme = "ph7x-reference"' in (chosen / "sardine.toml").read_text(encoding="utf-8")

    plain = tmp_path / "plain"
    assert runner.invoke(app, ["init", str(plain)]).exit_code == 0
    assert 'theme = "default"' in (plain / "sardine.toml").read_text(encoding="utf-8")


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


def test_admin_force_reset_enforces_password_policy_and_revokes_sessions(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    from cms_admin.security import verify_password
    from cms_core import AdminSession

    runner.invoke(app, ["init", str(tmp_path), "--name", "Demo"])
    created = runner.invoke(
        app,
        ["admin", "create-user", "chef", "-p", str(tmp_path)],
        input="tinned-fish-forever\ntinned-fish-forever\n",
    )
    assert created.exit_code == 0
    project = load_project(tmp_path)
    with project.open_storage() as storage:
        storage.save_session(
            AdminSession(
                token_hash="old-session",
                username="chef",
                csrf_token="old-csrf",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )

    weak = runner.invoke(
        app,
        ["admin", "create-user", "chef", "-p", str(tmp_path), "--force"],
        input="short\nshort\n",
    )
    assert weak.exit_code == 2

    reset = runner.invoke(
        app,
        ["admin", "create-user", "chef", "-p", str(tmp_path), "--force"],
        input="a-new-secure-password\na-new-secure-password\n",
    )
    assert reset.exit_code == 0
    with project.open_storage() as storage:
        user = storage.load_user("chef")
        assert user is not None
        assert verify_password(user.password_hash, "a-new-secure-password")
        assert storage.load_session("old-session") is None


def test_preview_serves_the_site_404_page(tmp_path: Path) -> None:
    """A missing path gets the site's own 404 page with status 404 — never
    the dev server's bare error page (production targets do the same)."""
    import http.server
    import threading
    import urllib.error
    import urllib.request
    from functools import partial

    from cms_cli.app import PreviewHandler

    (tmp_path / "404.html").write_text("<h1>Lost in orbit</h1>", encoding="utf-8")
    handler = partial(PreviewHandler, directory=str(tmp_path))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/definitely-missing"
            try:
                urllib.request.urlopen(url)
                raise AssertionError("expected a 404")
            except urllib.error.HTTPError as error:
                assert error.code == 404
                assert "Lost in orbit" in error.read().decode("utf-8")
        finally:
            server.shutdown()


def test_portable_round_trip_is_lossless(tmp_path: Path) -> None:
    """M6: dump -> import into a fresh project -> dump again produces
    byte-identical portable output — the portable pair really is the
    source of truth."""
    (tmp_path / "origin").mkdir()
    (tmp_path / "clone").mkdir()
    origin = make_project(tmp_path / "origin")
    runner.invoke(app, ["seed", "-p", str(origin)])
    dumped = runner.invoke(app, ["dump", "-p", str(origin)])
    assert dumped.exit_code == 0, dumped.output
    first = (origin / "portable" / "content.json").read_text(encoding="utf-8")

    clone = make_project(tmp_path / "clone")
    imported = runner.invoke(app, ["import", str(origin / "portable"), "-p", str(clone)])
    assert imported.exit_code == 0, imported.output
    redumped = runner.invoke(app, ["dump", "-p", str(clone)])
    assert redumped.exit_code == 0, redumped.output
    second = (clone / "portable" / "content.json").read_text(encoding="utf-8")
    assert first == second
    for path in sorted((origin / "portable" / "markdown").rglob("*.md")):
        relative = path.relative_to(origin / "portable")
        assert (clone / "portable" / relative).read_text(encoding="utf-8") == path.read_text(
            encoding="utf-8"
        ), relative
    blocked = runner.invoke(app, ["import", str(origin / "portable"), "-p", str(clone)])
    assert blocked.exit_code == 3  # refuses to overwrite without --replace


def test_import_wxr_into_a_fresh_project(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    export = tmp_path / "blog.xml"
    export.write_text(
        """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel><item>
    <title>Imported launch</title>
    <content:encoded><![CDATA[<p>From another blog.</p>]]></content:encoded>
    <wp:post_id>7</wp:post_id><wp:post_name>imported-launch</wp:post_name>
    <wp:status>draft</wp:status><wp:post_type>post</wp:post_type>
  </item></channel>
</rss>""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["import", str(export), "--format", "wxr", "-p", str(project)])
    assert result.exit_code == 0, result.output
    assert "imported 1 new WXR article(s)" in result.output
    with load_project(project).open_storage() as storage:
        article = storage.load_article("imported-launch")
    assert article is not None
    assert article.source.body_markdown == "From another blog."


def test_import_wxr_dry_run_reports_without_a_project(tmp_path: Path) -> None:
    export = tmp_path / "blog.xml"
    export.write_text(
        """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel>
  <item>
    <title>Kept post</title>
    <dc:creator><![CDATA[desk]]></dc:creator>
    <content:encoded><![CDATA[<p><img src="https://example.test/a.png"/></p>]]></content:encoded>
    <wp:post_id>1</wp:post_id><wp:post_type>post</wp:post_type>
    <wp:comment><wp:comment_id>9</wp:comment_id></wp:comment>
  </item>
  <item>
    <title>Old page</title>
    <wp:post_id>2</wp:post_id><wp:post_type>page</wp:post_type>
  </item>
  </channel>
</rss>""",
        encoding="utf-8",
    )

    # No project directory exists: the dry run must not need one.
    result = runner.invoke(app, ["import", str(export), "--format", "wxr", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "1 importable post(s) of 2 item(s)" in result.output
    assert "fidelity 50%" in result.output
    assert "authors: desk" in result.output
    assert "referenced media: 1 url(s)" in result.output
    assert "comments: 1 (not migrated)" in result.output
    assert 'page "Old page": pages are not migrated' in result.output


def test_import_wxr_rerun_never_duplicates(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    template = """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel><item>
    <title>{title}</title>
    <content:encoded><![CDATA[<p>{body}</p>]]></content:encoded>
    <wp:post_id>7</wp:post_id><wp:post_name>{slug}</wp:post_name>
    <wp:status>draft</wp:status><wp:post_type>post</wp:post_type>
  </item></channel>
</rss>"""
    export = tmp_path / "blog.xml"
    export.write_text(
        template.format(title="Launch", body="First take.", slug="launch"), encoding="utf-8"
    )
    first = runner.invoke(app, ["import", str(export), "--format", "wxr", "-p", str(project)])
    assert first.exit_code == 0, first.output

    # The source post was renamed upstream: same id, new slug and body.
    export.write_text(
        template.format(title="Launch day", body="Second take.", slug="launch-day"),
        encoding="utf-8",
    )
    rerun = runner.invoke(
        app, ["import", str(export), "--format", "wxr", "-p", str(project), "--replace"]
    )
    assert rerun.exit_code == 0, rerun.output
    assert "imported 0 new" in rerun.output
    assert "left 1 already-migrated untouched" in rerun.output
    with load_project(project).open_storage() as storage:
        assert storage.list_article_ids() == ["launch"]
        untouched = storage.load_article("launch")
    assert untouched is not None
    assert untouched.source.title == "Launch"

    updated = runner.invoke(
        app,
        ["import", str(export), "--format", "wxr", "-p", str(project), "--replace", "--update"],
    )
    assert updated.exit_code == 0, updated.output
    assert "updated 1" in updated.output
    with load_project(project).open_storage() as storage:
        assert storage.list_article_ids() == ["launch"]  # entity id survives the rename
        replaced = storage.load_article("launch")
    assert replaced is not None
    assert replaced.source.title == "Launch day"
    assert replaced.source.body_markdown == "Second take."


def test_import_wxr_mapping_previews_applies_and_warns(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    export = tmp_path / "blog.xml"
    export.write_text(
        """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel><item>
    <title>Mapped launch</title>
    <dc:creator><![CDATA[Old Desk]]></dc:creator>
    <content:encoded><![CDATA[<p>Body.</p>]]></content:encoded>
    <wp:post_id>8</wp:post_id><wp:post_name>mapped-launch</wp:post_name>
    <wp:status>draft</wp:status><wp:post_type>post</wp:post_type>
    <category domain="category" nicename="old-cat">Old cat</category>
    <category domain="post_tag" nicename="retired">Retired</category>
  </item></channel>
</rss>""",
        encoding="utf-8",
    )

    preview = runner.invoke(
        app,
        [
            "import",
            str(export),
            "--format",
            "wxr",
            "--dry-run",
            "--map-author",
            "Old Desk=New Desk",
            "--map-category",
            "old-cat=stories",
            "--map-tag",
            "retired=",
            "--map-tag",
            "absent=whatever",
        ],
    )
    assert preview.exit_code == 0, preview.output
    assert "authors: New Desk" in preview.output
    assert "categories: stories" in preview.output
    assert "tags: (none)" in preview.output
    assert 'warning: --map-tag "absent" matched nothing in this export' in preview.output

    imported = runner.invoke(
        app,
        [
            "import",
            str(export),
            "--format",
            "wxr",
            "-p",
            str(project),
            "--map-author",
            "Old Desk=New Desk",
            "--map-category",
            "old-cat=stories",
            "--map-tag",
            "retired=",
        ],
    )
    assert imported.exit_code == 0, imported.output
    with load_project(project).open_storage() as storage:
        article = storage.load_article("mapped-launch")
    assert article is not None
    assert article.author == "New Desk"
    assert article.category == "stories"
    assert article.tags == ()

    malformed = runner.invoke(
        app, ["import", str(export), "--format", "wxr", "--dry-run", "--map-author", "NoSeparator"]
    )
    assert malformed.exit_code == 2
    bad_slug = runner.invoke(
        app,
        [
            *["import", str(export), "--format", "wxr", "--dry-run"],
            "--map-category",
            "old-cat=Not A Slug",
        ],
    )
    assert bad_slug.exit_code == 2


def test_import_wxr_fetch_media_stores_and_rewrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_media_fetch import _png

    project = make_project(tmp_path)
    export = tmp_path / "blog.xml"
    export.write_text(
        """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel><item>
    <title>Illustrated launch</title>
    <content:encoded><![CDATA[<p><img
      src="https://example.test/img/rocket.png" alt="A rocket"/></p>]]></content:encoded>
    <wp:post_id>9</wp:post_id><wp:post_name>illustrated-launch</wp:post_name>
    <wp:status>draft</wp:status><wp:post_type>post</wp:post_type>
  </item></channel>
</rss>""",
        encoding="utf-8",
    )
    png = _png()
    monkeypatch.setattr("cms_core.media_fetch.default_fetcher", lambda url: (png, "image/png"))

    result = runner.invoke(
        app, ["import", str(export), "--format", "wxr", "-p", str(project), "--fetch-media"]
    )
    assert result.exit_code == 0, result.output
    assert "media: fetched https://example.test/img/rocket.png -> rocket" in result.output
    assert "media: 1 fetched, 0 reused, 0 failed" in result.output
    assert (project / "media" / "imported" / "rocket.png").read_bytes() == png
    with load_project(project).open_storage() as storage:
        article = storage.load_article("illustrated-launch")
        asset = storage.load_media_asset("rocket")
    assert article is not None and asset is not None
    assert "![A rocket](/media/imported/rocket.png)" in article.source.body_markdown
    assert asset.collection == "imported"

    conflict = runner.invoke(
        app, ["import", str(export), "--format", "wxr", "--dry-run", "--fetch-media"]
    )
    assert conflict.exit_code == 2


def test_import_wxr_records_redirects_for_changed_urls(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    template = """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel><item>
    <title>Launch</title>
    <link>https://old-site.test/2025/06/{slug}/</link>
    <content:encoded><![CDATA[<p>Body.</p>]]></content:encoded>
    <wp:post_id>7</wp:post_id><wp:post_name>{slug}</wp:post_name>
    <wp:status>publish</wp:status><wp:post_type>post</wp:post_type>
  </item></channel>
</rss>"""
    export = tmp_path / "blog.xml"
    export.write_text(template.format(slug="launch"), encoding="utf-8")

    first = runner.invoke(app, ["import", str(export), "--format", "wxr", "-p", str(project)])
    assert first.exit_code == 0, first.output
    assert "redirects: 1 source path(s) recorded" in first.output
    config = (project / "sardine.toml").read_text(encoding="utf-8")
    assert '"/2025/06/launch/" = "/blog/launch/"' in config

    # Idempotent: the same import leaves the file byte-identical.
    rerun = runner.invoke(
        app, ["import", str(export), "--format", "wxr", "-p", str(project), "--replace"]
    )
    assert rerun.exit_code == 0, rerun.output
    assert "map already covers" in rerun.output
    assert (project / "sardine.toml").read_text(encoding="utf-8") == config

    # Upstream rename + --update: the chain flattens to the newest address.
    export.write_text(template.format(slug="launch-day"), encoding="utf-8")
    renamed = runner.invoke(
        app,
        ["import", str(export), "--format", "wxr", "-p", str(project), "--replace", "--update"],
    )
    assert renamed.exit_code == 0, renamed.output
    updated = (project / "sardine.toml").read_text(encoding="utf-8")
    assert '"/2025/06/launch-day/" = "/blog/launch-day/"' in updated
    assert '"/2025/06/launch/" = "/blog/launch-day/"' in updated  # flattened, not chained
    assert '"/blog/launch-day/" =' not in updated  # a live address is never a source


def test_doctor_passes_on_a_healthy_project(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner.invoke(app, ["seed", "-p", str(project)])
    result = runner.invoke(app, ["doctor", "-p", str(project)])
    assert result.exit_code == 0, result.output
    assert "all checks passed" in result.output
    from cms_core.storage import MIGRATIONS

    assert f"schema {len(MIGRATIONS)}/{len(MIGRATIONS)}" in result.output
    assert "13 article(s), 2 page(s)" in result.output


def test_doctor_fails_on_missing_media_files(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner.invoke(app, ["seed", "-p", str(project)])
    (project / "media" / "images" / "rocket.svg").unlink()
    result = runner.invoke(app, ["doctor", "-p", str(project)])
    assert result.exit_code == 1
    assert "media: FAIL" in result.output
    assert "1 check(s) failed" in result.output


def test_doctor_fails_on_a_broken_extension(tmp_path: Path) -> None:
    (tmp_path / "sardine.toml").write_text(
        'extensions = ["definitely.missing:nope"]\n'
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n'
        '[storage]\nurl = "sqlite:///content.sqlite3"\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["doctor", "-p", str(tmp_path)])
    assert result.exit_code == 1
    assert "extensions: FAIL" in result.output


def test_demo_reaches_a_served_site_in_one_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#190: scaffold, seed, build and serve — one command, no
    questions; the directory persists for exploring afterwards."""
    import http.server

    class _InstantServer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "_InstantServer":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

    monkeypatch.setattr(http.server, "ThreadingHTTPServer", _InstantServer)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    assert "created" in result.output
    assert "seeded" in result.output
    assert "built" in result.output
    assert "Next steps:" in result.output
    assert (tmp_path / "sardine-demo" / "sardine.toml").is_file()
    assert (tmp_path / "sardine-demo" / "_site" / "index.html").is_file()
    # running again reuses everything without complaint
    again = runner.invoke(app, ["demo"])
    assert again.exit_code == 0, again.output
    assert "created" not in again.output
    assert "seeded" not in again.output
