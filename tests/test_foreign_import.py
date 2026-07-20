"""Foreign blog adapters stay explicit, deterministic and offline."""

from datetime import UTC, datetime

import pytest
from cms_core import ContentStatus, import_wordpress_wxr

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


def test_wordpress_wxr_maps_blog_posts_without_network_or_format_leakage() -> None:
    imported = import_wordpress_wxr(WXR)

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
    assert article.fields == {"wordpress_post_id": "41"}


def test_wordpress_wxr_rejects_dtds_and_entities() -> None:
    payload = b"""<?xml version="1.0"?>
<!DOCTYPE rss [<!ENTITY payload "must-not-expand">]>
<rss><channel><item><title>&payload;</title></item></channel></rss>"""

    with pytest.raises(ValueError, match="DTD or entity"):
        import_wordpress_wxr(payload)


def test_wordpress_wxr_collision_and_missing_date_fallback_are_deterministic() -> None:
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

    imported = import_wordpress_wxr(payload)
    second = imported.articles[1]
    assert second.id == "first-flight-2"
    assert second.status is ContentStatus.REVIEW
    assert second.created_at == datetime(1970, 1, 1, tzinfo=UTC)
