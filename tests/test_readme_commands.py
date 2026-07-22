"""The README must only teach commands that exist, and its flow must work.

Two failures shipped to users before this file existed:

1. The hero block told people to run `cms demo` right after installing. The
   command was on main but in no published release, so a clean `pip install`
   ended in "No such command 'demo'" on the very first instruction.

2. The install line pulled the reference theme, but `cms init` wrote
   `theme = "default"` and nothing ever selected the installed one. Readers
   followed the README exactly and got an unstyled page: navigation as a
   bullet list, content blocks running together.

Documentation that is never executed rots quietly. These tests execute it.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from cms_cli.app import app
from typer.testing import CliRunner

runner = CliRunner()
README = Path(__file__).resolve().parents[1] / "README.md"


def _commands() -> set[str]:
    """Every command name the CLI actually exposes, sub-apps included."""
    names: set[str] = set()
    for command in app.registered_commands:
        names.add(command.name or (command.callback.__name__ if command.callback else ""))
    for group in app.registered_groups:
        names.add(group.name or "")
    return {n.replace("_command", "").replace("_", "-") for n in names if n}


def _readme_commands() -> set[str]:
    """`cms <something>` as written inside the README's fenced blocks."""
    blocks = re.findall(r"```(?:bash|console|shell)\n(.*?)```", README.read_text("utf-8"), re.S)
    found: set[str] = set()
    for block in blocks:
        for line in block.splitlines():
            # tudo depois de # é prosa ("the cms command line"), não um comando
            for match in re.finditer(r"\bcms\s+([a-z][a-z-]*)", line.split("#")[0]):
                found.add(match.group(1))
    return found


def test_every_command_the_readme_teaches_exists() -> None:
    unknown = _readme_commands() - _commands()
    assert not unknown, (
        f"the README teaches commands that do not exist: {sorted(unknown)}. "
        f"Available: {sorted(_commands())}"
    )


def test_the_readme_flow_produces_a_themed_project(tmp_path: Path) -> None:
    """The documented flow must select a theme, not leave the bare default.

    Installing a theme package does nothing on its own: the project has to name
    it. If the README stops passing --theme, this fails.
    """
    text = README.read_text("utf-8")
    assert "--theme" in text, "the README no longer selects a theme in cms init"

    theme = re.search(r"cms init[^\n]*--theme\s+([a-z][\w-]*)", text)
    assert theme, "could not find the theme the README tells the reader to use"

    target = tmp_path / "from-readme"
    result = runner.invoke(app, ["init", str(target), "--theme", theme.group(1)])
    assert result.exit_code == 0, result.output

    config = tomllib.loads((target / "sardine.toml").read_text("utf-8"))
    assert config["site"]["theme"] == theme.group(1)
    assert config["site"]["theme"] != "default"
