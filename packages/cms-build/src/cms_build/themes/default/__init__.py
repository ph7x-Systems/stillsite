"""Built-in minimal theme: semantic HTML, zero inline styles, local assets."""

from collections.abc import Mapping
from importlib import resources

from jinja2 import Environment, PackageLoader, select_autoescape


class DefaultTheme:
    name = "default"

    def __init__(self) -> None:
        self._environment = Environment(
            loader=PackageLoader("cms_build.themes.default", "templates"),
            autoescape=select_autoescape(default=True, default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, kind: str, context: Mapping[str, object]) -> str:
        template = self._environment.get_template(f"{kind}.html.j2")
        return template.render(**context) + "\n"

    def assets(self) -> Mapping[str, bytes]:
        package = resources.files("cms_build.themes.default") / "assets"
        return {
            f"assets/{entry.name}": entry.read_bytes()
            for entry in sorted(package.iterdir(), key=lambda item: item.name)
            if entry.is_file()
        }
