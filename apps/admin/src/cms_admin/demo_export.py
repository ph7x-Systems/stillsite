"""Static, read-only snapshot of the admin for the public demo site.

The demo site is a static host, so it cannot run the admin — but it can
show it. This module boots the real admin against a throwaway copy of the
content database, signs in as a generated demo user, crawls every editorial
page and writes them as static HTML under a prefix (``/admin/`` on the demo
site). The snapshot is read-only by construction: there is no server behind
it, forms are neutralized, buttons disabled, and a banner says so. Nothing a
visitor does can save anything anywhere.

Usage: ``python -m cms_admin.demo_export --storage content.sqlite3 --out
_site/admin``.
"""

import argparse
import re
import secrets
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cms_core import Role, User, create_storage
from cms_core.languages import TARGET_LANGUAGES

from cms_admin.app import create_app
from cms_admin.settings import AdminSettings

PREFIX = "/admin"

BANNER = (
    '<div class="admin-demo-note" role="note">Read-only demo — nothing here is saved. '
    "This is a static snapshot of the Sardine CMS admin; install "
    '<a href="https://github.com/ph7x-Systems/sardine-cms">Sardine CMS</a> to run the real one.'
    "</div>"
)

BANNER_CSS = (
    "<style>.admin-demo-note{background:#1b1a12;color:#e0d5ac;padding:.6rem 1.2rem;"
    "font-size:.85rem;border-bottom:1px solid #3a3420}.admin-demo-note a{color:inherit;"
    "text-decoration:underline}button[disabled]{cursor:not-allowed}</style>"
)


def neutralize(html: str) -> str:
    """Make a captured page inert: prefixed links, no forms, no tokens."""
    html = html.replace('href="/', f'href="{PREFIX}/')
    # The live admin serves /preview/ itself; in the static snapshot the
    # public site *is* the preview, so every preview link maps onto the
    # site: /preview/ -> /, /preview/blog/x/ -> /blog/x/.
    html = html.replace(f'href="{PREFIX}/preview/', 'href="/')
    html = html.replace('src="/', f'src="{PREFIX}/')
    html = html.replace('action="/', f'action="{PREFIX}/')
    html = html.replace('method="post"', 'method="get"')
    html = re.sub(r'<input type="hidden" name="csrf_token" value="[^"]*">', "", html)
    html = html.replace('<button type="submit"', '<button type="button" disabled')
    html = html.replace("</head>", f"{BANNER_CSS}</head>")
    html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BANNER, html, count=1)
    return html


def _demo_paths(storage_path: Path) -> list[str]:
    """Every page worth capturing, enumerated from the content itself."""
    paths = [
        "/login",
        "/",
        "/articles",
        "/articles/new",
        "/pages",
        "/pages/new",
        "/media",
        "/translations",
        "/calendar",
        "/activity",
        "/submissions",
        "/media/new",
        "/publishing",
        "/trash",
        "/users",
        "/menu",
    ]
    with create_storage(f"sqlite:///{storage_path}") as storage:
        paths.extend(f"/media/{asset_id}" for asset_id in storage.list_media_ids())
        for article_id in storage.list_article_ids():
            paths.append(f"/articles/{article_id}")
            paths.extend(
                f"/articles/{article_id}/translations/{language.value}"
                for language in TARGET_LANGUAGES
            )
        for page_id in storage.list_page_ids():
            paths.append(f"/pages/{page_id}")
            paths.extend(
                f"/pages/{page_id}/translations/{language.value}" for language in TARGET_LANGUAGES
            )
            page = storage.load_page(page_id)
            for section in page.sections if page else []:
                paths.append(f"/pages/{page_id}/sections/{section.key}")
                paths.extend(
                    f"/pages/{page_id}/sections/{section.key}/translations/{language.value}"
                    for language in TARGET_LANGUAGES
                )
    return paths


def export_demo(
    storage_file: Path,
    out_dir: Path,
    media_dir: Path | None = None,
    project_dir: Path | None = None,
) -> int:
    """Write the static admin snapshot; returns the number of pages."""
    from fastapi.testclient import TestClient

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        db_copy = Path(scratch) / "demo.sqlite3"
        shutil.copyfile(storage_file, db_copy)
        password = secrets.token_urlsafe(24)
        with create_storage(f"sqlite:///{db_copy}") as storage:
            from cms_admin.security import hash_password

            storage.save_user(
                User(
                    username="demo",
                    password_hash=hash_password(password),
                    role=Role.ADMIN,
                    created_at=datetime.now(UTC),
                )
            )
        settings = AdminSettings(
            storage_url=f"sqlite:///{db_copy}",
            cookie_secure=False,
            media_dir=media_dir if media_dir is not None else Path(scratch) / "media",
            project_dir=project_dir if project_dir is not None else Path(scratch),
        )
        app = create_app(settings)
        pages = 0
        with TestClient(app) as client:
            form = client.get("/login")
            client.post(
                "/login",
                data={
                    "username": "demo",
                    "password": password,
                    "login_csrf": form.cookies["sardine_login_csrf"],
                },
            )
            for path in _demo_paths(db_copy):
                response = client.get(path)
                if response.status_code != 200:
                    continue
                target = out_dir / path.lstrip("/") / "index.html"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(neutralize(response.text), encoding="utf-8")
                pages += 1
    static_src = Path(__file__).parent / "static"
    shutil.copytree(static_src, out_dir / "static", dirs_exist_ok=True)
    if media_dir is not None and media_dir.is_dir():
        shutil.copytree(media_dir, out_dir / "media-files", dirs_exist_ok=True)
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, required=True, help="SQLite content database")
    parser.add_argument("--out", type=Path, required=True, help="output directory (…/admin)")
    parser.add_argument("--media-dir", type=Path, default=None, help="project media directory")
    parser.add_argument("--project-dir", type=Path, default=None, help="project directory")
    arguments = parser.parse_args(argv)
    pages = export_demo(
        arguments.storage, arguments.out, arguments.media_dir, arguments.project_dir
    )
    print(f"captured {pages} admin page(s) into {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
