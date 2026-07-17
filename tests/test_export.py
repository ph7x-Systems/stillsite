"""Deterministic export of the portable JSON/Markdown source of truth."""

import json
from datetime import UTC, datetime

from cms_core import Article, ArticleContent, Language, new_article
from cms_core.export import export_content_json, export_markdown_files, languages_in_export

FIXED_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)


def make_articles() -> list[Article]:
    zebra = new_article("zebra", ArticleContent(title="Zebra"), now=FIXED_NOW)
    alpha = new_article("alpha", ArticleContent(title="Alpha", summary="A."), now=FIXED_NOW)
    alpha.set_translation(Language.PT_PT, ArticleContent(title="Alfa", summary="A."))
    return [zebra, alpha]


def test_export_is_deterministic_and_sorted() -> None:
    first = export_content_json(make_articles())
    second = export_content_json(make_articles())
    assert first == second

    payload = json.loads(first)
    ids = [entry["id"] for entry in payload["articles"]]
    assert ids == sorted(ids)
    assert payload["schema_version"] == 1


def test_export_records_translation_states() -> None:
    payload = json.loads(export_content_json(make_articles()))
    alpha = next(entry for entry in payload["articles"] if entry["id"] == "alpha")
    assert alpha["languages"]["en"]["state"] == "complete"
    assert alpha["languages"]["pt-pt"]["state"] == "complete"
    assert "es" not in alpha["languages"]


def test_markdown_export_writes_one_file_per_language() -> None:
    files = export_markdown_files(make_articles())
    assert "alpha/en.md" in files
    assert "alpha/pt-pt.md" in files
    assert "zebra/en.md" in files
    assert files["alpha/pt-pt.md"].startswith("# Alfa\n")
    assert languages_in_export(files) == {Language.EN, Language.PT_PT}


def test_markdown_files_end_with_single_newline() -> None:
    for content in export_markdown_files(make_articles()).values():
        assert content.endswith("\n")
        assert not content.endswith("\n\n")
