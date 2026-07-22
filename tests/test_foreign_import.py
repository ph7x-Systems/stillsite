"""Foreign blog adapters stay explicit, deterministic and offline."""

from datetime import UTC, datetime

import pytest
from cms_core import ContentStatus, import_wxr, inspect_wxr

WXR = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"
 xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
 xmlns:content="http://purl.org/rss/1.0/modules/content/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
  <item>
    <title>First flight</title>
    <dc:creator><![CDATA[Editorial desk]]></dc:creator>
    <content:encoded><![CDATA[
      <p>Hello <strong>orbit</strong>.</p>
      <p><a href="https://example.test/path">Read more</a></p>
    ]]></content:encoded>
    <excerpt:encoded><![CDATA[<p>A short launch note.</p>]]></excerpt:encoded>
    <wp:post_id>41</wp:post_id>
    <wp:post_date_gmt>2025-06-02 09:30:00</wp:post_date_gmt>
    <wp:post_name>first-flight</wp:post_name>
    <wp:status>publish</wp:status>
    <wp:post_type>post</wp:post_type>
    <category domain="category" nicename="mission-log"><![CDATA[Mission log]]></category>
    <category domain="post_tag" nicename="test-flight"><![CDATA[Test flight]]></category>
  </item>
  <item>
    <title>Unsupported page</title>
    <wp:post_id>42</wp:post_id>
    <wp:post_type>page</wp:post_type>
  </item>
</channel>
</rss>
"""


def test_wxr_maps_blog_posts_without_network_or_format_leakage() -> None:
    imported = import_wxr(WXR)

    assert imported.skipped == 1
    assert len(imported.articles) == 1
    article = imported.articles[0]
    assert article.id == "first-flight"
    assert article.status is ContentStatus.PUBLISHED
    assert article.created_at == datetime(2025, 6, 2, 9, 30, tzinfo=UTC)
    assert article.source.summary == "A short launch note."
    assert article.source.body_markdown == (
        "Hello **orbit**.\n\n[Read more](https://example.test/path)"
    )
    assert article.category == "mission-log"
    assert article.tags == ("test-flight",)
    assert article.author == "Editorial desk"
    assert article.fields == {"wxr_post_id": "41"}


def test_wxr_rejects_dtds_and_entities() -> None:
    payload = b"""<?xml version="1.0"?>
<!DOCTYPE rss [<!ENTITY payload "must-not-expand">]>
<rss><channel><item><title>&payload;</title></item></channel></rss>"""

    with pytest.raises(ValueError, match="DTD or entity"):
        import_wxr(payload)

    encoded = (
        payload.decode("utf-8").replace('encoding="UTF-8"', 'encoding="UTF-16"').encode("utf-16")
    )
    with pytest.raises(ValueError, match="DTD or entity"):
        import_wxr(encoded)


def test_wxr_collision_and_missing_date_fallback_are_deterministic() -> None:
    payload = WXR.replace(
        b"</channel>",
        b"""<item>
          <title>First flight</title>
          <wp:post_id>43</wp:post_id>
          <wp:post_name>first-flight</wp:post_name>
          <wp:status>pending</wp:status>
          <wp:post_type>post</wp:post_type>
        </item></channel>""",
    )

    imported = import_wxr(payload)
    second = imported.articles[1]
    assert second.id == "first-flight-2"
    assert second.status is ContentStatus.REVIEW
    assert second.created_at == datetime(1970, 1, 1, tzinfo=UTC)


MIXED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"
 xmlns:content="http://purl.org/rss/1.0/modules/content/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
  <item>
    <title>Kept post</title>
    <dc:creator><![CDATA[Editorial desk]]></dc:creator>
    <content:encoded><![CDATA[<p><img src="https://example.test/b.png"/>
      <IMG SRC='https://example.test/a.png'></p>]]></content:encoded>
    <wp:post_id>1</wp:post_id>
    <wp:post_type>post</wp:post_type>
    <category domain="category" nicename="mission-log">Mission log</category>
    <category domain="post_tag" nicename="test-flight">Test flight</category>
    <wp:comment><wp:comment_id>11</wp:comment_id></wp:comment>
    <wp:comment><wp:comment_id>12</wp:comment_id></wp:comment>
  </item>
  <item>
    <title>Old page</title>
    <wp:post_id>2</wp:post_id>
    <wp:post_type>page</wp:post_type>
  </item>
  <item>
    <title>Rocket photo</title>
    <wp:post_id>3</wp:post_id>
    <wp:post_type>attachment</wp:post_type>
    <wp:attachment_url>https://example.test/rocket.jpg</wp:attachment_url>
  </item>
  <item>
    <title>Menu entry</title>
    <wp:post_id>4</wp:post_id>
    <wp:post_type>nav_menu_item</wp:post_type>
  </item>
  <item>
    <title></title>
    <wp:post_id>5</wp:post_id>
    <wp:post_type>post</wp:post_type>
  </item>
</channel>
</rss>"""


def test_inspect_accounts_for_every_item() -> None:
    report = inspect_wxr(MIXED)

    assert report.posts == 1
    assert report.total_items == 5
    assert report.fidelity == 20.0
    assert report.authors == ("Editorial desk",)
    assert report.categories == ("mission-log",)
    assert report.tags == ("test-flight",)
    assert report.media_urls == (
        "https://example.test/a.png",
        "https://example.test/b.png",
        "https://example.test/rocket.jpg",
    )
    assert report.comments == 2
    # Nothing is silently dropped: one note per non-imported item.
    notes = {(note.kind, note.title): note.reason for note in report.left_behind}
    assert notes[("page", "Old page")].startswith("pages are not migrated")
    assert notes[("attachment", "Rocket photo")] == "media files are not fetched by the importer"
    assert notes[("nav_menu_item", "Menu entry")] == "navigation belongs to the target site"
    assert notes[("post", "(untitled)")] == "post has no title"
    # The report and the importer agree on what gets in.
    assert len(import_wxr(MIXED).articles) == report.posts


def test_inspect_of_an_empty_channel_reports_full_fidelity() -> None:
    report = inspect_wxr(b"<rss><channel></channel></rss>")
    assert report.total_items == 0
    assert report.fidelity == 100.0
    assert report.left_behind == ()
