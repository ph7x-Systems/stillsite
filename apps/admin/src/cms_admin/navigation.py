"""The admin navigation registry: one declaration per screen.

The sidebar, the section labels and the demo snapshot's page list all
derive from here — adding a screen is one registration in its module,
never a template edit. Labels are catalog msgids translated at render
time; extensions can register screens through the same call.
"""

from dataclasses import dataclass

from cms_core import Role

ROLE_ORDER = (Role.EDITOR, Role.REVIEWER, Role.PUBLISHER, Role.ADMIN)


@dataclass(frozen=True, slots=True)
class AdminScreen:
    key: str
    path: str
    label: str
    """A catalog msgid — translated where it renders."""
    icon: str
    order: int
    minimum_role: Role = Role.EDITOR
    in_sidebar: bool = True
    group: str = ""
    """Optional nav-header msgid rendered before this screen when the
    group changes between consecutive sidebar items."""


_SCREENS: dict[str, AdminScreen] = {}


def register_screen(screen: AdminScreen) -> None:
    existing = _SCREENS.get(screen.key)
    if existing is not None and existing != screen:
        raise ValueError(f"admin screen {screen.key!r} is already registered differently")
    _SCREENS[screen.key] = screen


def sidebar_screens(role: Role | None) -> list[AdminScreen]:
    """The sidebar for one role, in declared order."""
    if role is None:
        return []
    rank = ROLE_ORDER.index(role)
    return sorted(
        (
            screen
            for screen in _SCREENS.values()
            if screen.in_sidebar and ROLE_ORDER.index(screen.minimum_role) <= rank
        ),
        key=lambda screen: screen.order,
    )


def section_labels() -> dict[str, str]:
    """Section key -> label msgid (breadcrumbs and page titles)."""
    return {screen.key: screen.label for screen in _SCREENS.values()}


def snapshot_paths() -> list[str]:
    """Every registered screen's path — the demo snapshot's capture
    list derives from the registry, never from a hand-kept list."""
    return [screen.path for screen in sorted(_SCREENS.values(), key=lambda screen: screen.order)]
