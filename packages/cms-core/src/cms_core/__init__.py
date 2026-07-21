"""Content model, versioned schemas and translation states."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from cms_core.accounts import AdminSession, PasswordReset, Role, User
from cms_core.extensions import (
    ENTRY_POINT_GROUP,
    CommentsProvider,
    Extension,
    ExtensionError,
    load_extensions,
)
from cms_core.foreign import WxrImport, import_wxr
from cms_core.forms import FormSubmission
from cms_core.language_packs import (
    LanguagePack,
    language_pack,
    register_language_pack,
)
from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import (
    SCHEMA_VERSION,
    Article,
    ArticleContent,
    new_article,
)
from cms_core.pages import Page, PageContent, Section, SectionContent, new_page
from cms_core.portable import import_content_json
from cms_core.preview_links import PreviewLink
from cms_core.section_kinds import SectionKindSpec
from cms_core.states import ContentStatus, TranslationState
from cms_core.storage import StorageBackend, create_storage
from cms_core.translatable import (
    ChecksummedContent,
    TranslatableModel,
    Translation,
    worst_state,
)

try:
    __version__ = _dist_version("sardine-cms-core")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = [
    "ENTRY_POINT_GROUP",
    "SCHEMA_VERSION",
    "SOURCE_LANGUAGE",
    "TARGET_LANGUAGES",
    "AdminSession",
    "Article",
    "ArticleContent",
    "ChecksummedContent",
    "CommentsProvider",
    "ContentStatus",
    "Extension",
    "ExtensionError",
    "FormSubmission",
    "Language",
    "LanguagePack",
    "MediaAsset",
    "MenuItem",
    "Page",
    "PageContent",
    "PasswordReset",
    "PreviewLink",
    "Role",
    "Section",
    "SectionContent",
    "SectionKindSpec",
    "StorageBackend",
    "TranslatableModel",
    "Translation",
    "TranslationState",
    "User",
    "WxrImport",
    "create_storage",
    "import_content_json",
    "import_wxr",
    "language_pack",
    "load_extensions",
    "new_article",
    "new_page",
    "register_language_pack",
    "worst_state",
]
