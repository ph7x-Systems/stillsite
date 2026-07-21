"""Translation-state and publishing-gate behavior of the article model."""

import pytest
from cms_core import (
    SOURCE_LANGUAGE,
    TARGET_LANGUAGES,
    ArticleContent,
    Language,
    TranslationState,
    new_article,
)


def test_new_article_has_all_target_translations_missing() -> None:
    article = new_article("hello-world", ArticleContent(title="Hello"))
    assert article.incomplete_languages() == TARGET_LANGUAGES
    assert all(state is TranslationState.MISSING for state in article.translation_states().values())
    assert not article.can_publish()


def test_source_language_is_always_complete() -> None:
    article = new_article("hello-world", ArticleContent(title="Hello"))
    assert article.translation_state(SOURCE_LANGUAGE) is TranslationState.COMPLETE


def test_translation_becomes_complete_then_outdated_when_source_changes() -> None:
    article = new_article("hello-world", ArticleContent(title="Hello", body_markdown="Body"))
    article.set_translation(Language.PT_PT, ArticleContent(title="Olá", body_markdown="Corpo"))
    assert article.translation_state(Language.PT_PT) is TranslationState.COMPLETE

    article.source = ArticleContent(title="Hello v2", body_markdown="Body v2")
    assert article.translation_state(Language.PT_PT) is TranslationState.OUTDATED


def test_can_publish_requires_all_required_languages_complete() -> None:
    article = new_article("hello-world", ArticleContent(title="Hello"))
    for language in TARGET_LANGUAGES:
        article.set_translation(language, ArticleContent(title=f"Hello {language}"))
    assert article.can_publish()

    article.source = ArticleContent(title="Changed")
    assert not article.can_publish()
    assert article.can_publish(required_languages=())


def test_cannot_set_translation_for_source_language() -> None:
    article = new_article("hello-world", ArticleContent(title="Hello"))
    with pytest.raises(ValueError, match="source language"):
        article.set_translation(SOURCE_LANGUAGE, ArticleContent(title="Hello"))


def test_article_id_must_be_a_slug() -> None:
    with pytest.raises(ValueError):
        new_article("Not A Slug!", ArticleContent(title="Hello"))


def test_empty_items_and_body_keep_the_legacy_checksum() -> None:
    """ADR-0037: adding the new fields must not flip existing
    translations to outdated — the checksum only changes when the new
    fields hold content."""
    from cms_core.pages import PageContent, SectionContent

    legacy_section = SectionContent(fields={"heading": "Hi"}, media=["logo"])
    assert (
        legacy_section.checksum()
        == SectionContent(fields={"heading": "Hi"}, media=["logo"], items=[]).checksum()
    )
    with_items = SectionContent(fields={"heading": "Hi"}, media=["logo"], items=[{"q": "?"}])
    assert with_items.checksum() != legacy_section.checksum()

    legacy_page = PageContent(title="Home", slug="home")
    explicit_empty = PageContent(title="Home", slug="home", body_markdown="")
    assert legacy_page.checksum() == explicit_empty.checksum()
    with_body = PageContent(title="Home", slug="home", body_markdown="x")
    assert with_body.checksum() != legacy_page.checksum()


def test_item_edits_flip_translations_to_outdated() -> None:
    from cms_core.pages import Section, SectionContent

    section = Section(
        key="faq",
        kind="faq",
        source=SectionContent(items=[{"question": "A?", "answer": "B."}]),
    )
    section.set_translation(
        Language.PT_PT, SectionContent(items=[{"question": "A?", "answer": "B?"}])
    )
    assert section.translation_state(Language.PT_PT) is TranslationState.COMPLETE
    section.source.items.append({"question": "C?", "answer": "D."})
    assert section.translation_state(Language.PT_PT) is TranslationState.OUTDATED
