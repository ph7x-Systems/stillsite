"""Accessibility gate: run axe-core over the built example site.

Serves the given build directory, drives headless Chromium (Playwright) over
representative pages and fails on any serious/critical axe violation.
Used locally and by the CI `Accessibility (axe)` job — one script, one truth.

Usage:
    python scripts/a11y_check.py <site_dir> <axe_min_js> [--scheme light|dark|both] [pages...]

`--scheme` emulates `prefers-color-scheme`; `both` audits every page twice.
Pages that honor the scheme (the admin's AdminLTE theme init) must pass
WCAG in both palettes — the tokens are only as good as their contrast.
"""

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = [
    "/",
    "/pt-pt/",
    "/blog/",
    "/pt-pt/blog/",
    "/blog/we-choose-the-tin/",
    "/crew/",
    "/404.html",
]

FAIL_IMPACTS = {"serious", "critical"}


def _serve(directory: Path) -> tuple[socketserver.TCPServer, int]:
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(directory), **kwargs
    )
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def main() -> int:
    args = sys.argv[1:]
    scheme = "light"
    if "--scheme" in args:
        at = args.index("--scheme")
        scheme = args[at + 1]
        del args[at : at + 2]
    site_dir = Path(args[0]).resolve()
    axe_source = Path(args[1]).read_text(encoding="utf-8")
    pages = args[2:] or PAGES
    schemes = ["light", "dark"] if scheme == "both" else [scheme]
    server, port = _serve(site_dir)
    failures: list[str] = []
    audited = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for color_scheme in schemes:
                page = browser.new_page(color_scheme=color_scheme)  # type: ignore[arg-type]
                for path in pages:
                    page.goto(f"http://127.0.0.1:{port}{path}", wait_until="load")
                    page.evaluate(axe_source)
                    result = page.evaluate("() => axe.run(document)")
                    audited += 1
                    for violation in result["violations"]:
                        if violation["impact"] in FAIL_IMPACTS:
                            nodes = ", ".join(
                                n["target"][0] for n in violation["nodes"][:3] if n["target"]
                            )
                            failures.append(
                                f"{path} [{color_scheme}]: [{violation['impact']}] "
                                f"{violation['id']} — {violation['help']} ({nodes})"
                            )
                page.close()
            browser.close()
    finally:
        server.shutdown()
    if failures:
        print(json.dumps(failures, indent=2, ensure_ascii=False))
        print(f"FAIL: {len(failures)} serious/critical accessibility violations")
        return 1
    print(f"OK: no serious/critical axe violations across {audited} page renders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
