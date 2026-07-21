"""The #129 performance bar, reproducibly: admin search under 300 ms
on a 10 000-entry database.

Method (the ROADMAP measurement rules): dataset = 5 000 articles with
one translation each + 4 000 pages with one section each + 1 000 media
assets, seeded deterministically; the measured span is
``storage.search_content(...)`` alone (the admin route adds template
rendering, not query time); 5 runs per needle after 1 warm-up; the
reported number is the worst run (a stricter percentile than p95 at
this run count). Engine = SQLite by default; set SARDINE_BENCH_URL to
measure another engine. Exit 1 over budget.

Usage:
    python scripts/search_bench.py [--budget-ms 300]
"""

import os
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from cms_core import Language, MediaAsset, create_storage
from cms_core.models import ArticleContent, new_article
from cms_core.pages import PageContent, Section, SectionContent, new_page
from cms_core.storage import StorageBackend

NOW = datetime(2026, 1, 15, tzinfo=UTC)
NEEDLES = ("orbital", "lata", "viagem-9999", "nothing-matches-this")


def _seed(storage: "StorageBackend") -> None:
    for index in range(5000):
        article = new_article(
            f"entry-{index}",
            ArticleContent(
                title=f"Orbital note {index}",
                summary=f"Summary {index}",
                body_markdown=f"Body text number {index} about tins.",
            ),
            now=NOW,
        )
        article.set_translation(
            Language.PT_PT,
            ArticleContent(title=f"Nota orbital {index}", summary=f"Resumo {index}"),
        )
        storage.save_article(article)
    for index in range(4000):
        page = new_page(
            f"page-{index}",
            PageContent(title=f"Voyage page {index}", slug=f"viagem-{index}"),
            now=NOW,
        )
        page.sections.append(
            Section(
                key="faq",
                kind="faq",
                source=SectionContent(items=[{"question": f"Q{index}?", "answer": "A."}]),
            )
        )
        storage.save_page(page)
    for index in range(1000):
        storage.save_media_asset(
            MediaAsset(
                id=f"asset-{index}",
                path=f"images/asset-{index}.svg",
                mime_type="image/svg+xml",
                width=8,
                height=8,
                alt={Language.EN: f"Asset {index} of the tin fleet"},
            )
        )


def main() -> int:
    budget_ms = 300.0
    if "--budget-ms" in sys.argv:
        budget_ms = float(sys.argv[sys.argv.index("--budget-ms") + 1])
    with tempfile.TemporaryDirectory() as scratch:
        url = os.environ.get("SARDINE_BENCH_URL", f"sqlite:///{Path(scratch) / 'bench.sqlite3'}")
        with create_storage(url) as storage:
            print("seeding 10 000 entries...")
            seeded_from = time.monotonic()
            _seed(storage)
            print(f"seeded in {time.monotonic() - seeded_from:.1f}s; measuring")
            worst = 0.0
            storage.search_content("warm-up")
            for needle in NEEDLES:
                runs = []
                for _ in range(5):
                    started = time.perf_counter()
                    hits = storage.search_content(needle)
                    runs.append((time.perf_counter() - started) * 1000)
                slowest = max(runs)
                worst = max(worst, slowest)
                print(f"  {needle!r}: worst {slowest:.1f} ms, {len(hits)} hit(s)")
    print(f"worst case: {worst:.1f} ms (budget {budget_ms:.0f} ms)")
    if worst > budget_ms:
        print("FAIL: over budget")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
