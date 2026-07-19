"""Sardine CMS admin panel (ADR-0013): FastAPI API + server-rendered UI."""

from cms_admin.app import create_app
from cms_admin.settings import AdminSettings

__all__ = ["AdminSettings", "create_app"]
