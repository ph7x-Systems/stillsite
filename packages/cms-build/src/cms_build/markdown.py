"""Safe Markdown rendering: CommonMark with raw HTML disabled.

Editors can never inject raw HTML through article bodies — rich components
arrive later via reviewed custom blocks (see the extensibility contracts).
"""

from markdown_it import MarkdownIt

_renderer = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})


def render_markdown(text: str) -> str:
    return _renderer.render(text)
