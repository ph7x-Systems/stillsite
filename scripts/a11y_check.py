"""Accessibility gate: run axe-core over the built example site.

Serves the given build directory, drives headless Chromium (Playwright) over
representative pages and fails on any serious/critical axe violation.
Used locally and by the CI `Accessibility (axe)` job — one script, one truth.

Usage:
    python scripts/a11y_check.py <site_dir> <axe_min_js> [pages...]
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
    site_dir = Path(sys.argv[1]).resolve()
    axe_source = Path(sys.argv[2]).read_text(encoding="utf-8")
    pages = sys.argv[3:] or PAGES
    server, port = _serve(site_dir)
    failures: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            for path in pages:
                page.goto(f"http://127.0.0.1:{port}{path}", wait_until="load")
                page.evaluate(axe_source)
                result = page.evaluate("() => axe.run(document)")
                for violation in result["violations"]:
                    if violation["impact"] in FAIL_IMPACTS:
                        nodes = ", ".join(
                            n["target"][0] for n in violation["nodes"][:3] if n["target"]
                        )
                        failures.append(
                            f"{path}: [{violation['impact']}] {violation['id']} — "
                            f"{violation['help']} ({nodes})"
                        )
            browser.close()
    finally:
        server.shutdown()
    if failures:
        print(json.dumps(failures, indent=2, ensure_ascii=False))
        print(f"FAIL: {len(failures)} serious/critical accessibility violations")
        return 1
    print(f"OK: no serious/critical axe violations across {len(pages)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
