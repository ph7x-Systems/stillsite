"""The admin navigation registry: one declaration drives everything.

The sidebar, the section labels and the demo snapshot's capture list
all derive from the registry — a screen registered once appears in all
three, respecting its role and order; a conflicting re-registration is
loud.
"""

# Importing the app package plus every screen module runs the registrations,
# exactly as create_app does.
import cms_admin.activity_view
import cms_admin.app
import cms_admin.calendar_view
import cms_admin.translations_queue  # noqa: F401
import pytest
from cms_admin.navigation import (
    _SCREENS,
    AdminScreen,
    register_screen,
    section_labels,
    sidebar_screens,
    snapshot_paths,
)
from cms_core import Role


def test_one_registration_reaches_sidebar_labels_and_snapshot() -> None:
    screen = AdminScreen("nav-probe", "/nav-probe", "Probe", "bi-bug", 999, Role.ADMIN)
    register_screen(screen)
    try:
        assert screen in sidebar_screens(Role.ADMIN)
        assert screen not in sidebar_screens(Role.EDITOR)  # role-gated
        assert section_labels()["nav-probe"] == "Probe"
        assert "/nav-probe" in snapshot_paths()
    finally:
        _SCREENS.pop("nav-probe", None)


def test_sidebar_respects_declared_order_and_roles() -> None:
    editor = sidebar_screens(Role.EDITOR)
    admin = sidebar_screens(Role.ADMIN)
    assert [s.order for s in admin] == sorted(s.order for s in admin)
    assert {s.key for s in editor} <= {s.key for s in admin}
    assert "activity" not in {s.key for s in editor}
    assert "activity" in {s.key for s in admin}
    assert sidebar_screens(None) == []


def test_conflicting_reregistration_is_loud() -> None:
    original = _SCREENS["dashboard"]
    register_screen(original)  # identical: idempotent
    with pytest.raises(ValueError, match="already registered differently"):
        register_screen(AdminScreen("dashboard", "/elsewhere", "Dashboard", "bi-speedometer", 10))
