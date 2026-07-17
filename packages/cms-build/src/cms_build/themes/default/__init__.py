"""Built-in minimal theme: semantic HTML, zero inline styles, local assets.

Projects can override any template or asset without forking: files under the
project's ``theme/templates`` and ``theme/assets`` directories take precedence
over the theme's own (ADR-0007).
"""

from collections.abc import Mapping
from importlib import resources
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, select_autoescape


class DefaultTheme:
    name = "default"

    def __init__(self, overrides: Path | None = None) -> None:
        self._overrides = overrides
        loaders: list[FileSystemLoader | PackageLoader] = []
        if overrides is not None and (overrides / "templates").is_dir():
            loaders.append(FileSystemLoader(overrides / "templates"))
        loaders.append(PackageLoader("cms_build.themes.default", "templates"))
        self._environment = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(default=True, default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, kind: str, context: Mapping[str, object]) -> str:
        template = self._environment.get_template(f"{kind}.html.j2")
        return template.render(**context) + "\n"

    def assets(self) -> Mapping[str, bytes]:
        package = resources.files("cms_build.themes.default") / "assets"
        merged: dict[str, bytes] = {
            f"assets/{entry.name}": entry.read_bytes()
            for entry in sorted(package.iterdir(), key=lambda item: item.name)
            if entry.is_file()
        }
        if self._overrides is not None and (self._overrides / "assets").is_dir():
            for path in sorted((self._overrides / "assets").iterdir()):
                if path.is_file():
                    merged[f"assets/{path.name}"] = path.read_bytes()
        return merged
