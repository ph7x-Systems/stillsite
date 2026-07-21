"""One deployment contract, any destination (#156).

The conformance suite runs the same rules over every provider — the two
bundled ones (filesystem, swa) and a fictional third one defined right
here and registered through an extension. That third provider proves
the design end to end: a new destination is one factory implementing
the contract; the core, the editor and the publish flow never change.
"""

import shutil
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_build.deploy import (
    DEPLOY_CONTRACT_VERSION,
    DeployError,
    DeployLocked,
    DeployProvider,
    DeployState,
    FilesystemDeployer,
    ReleaseInfo,
    available_deploy_providers,
    create_deploy_provider,
    register_deploy_provider,
)
from cms_core import Role, User, create_storage
from cms_core.extensions import Extension
from cms_core.models import ArticleContent, new_article
from fastapi.testclient import TestClient
from test_deploy_swa import NOW, PASSWORD, TOKEN, MockSwa

PAYLOAD_V1 = {"sitemap.xml": b"<urlset/>", "index.html": b"v1"}
PAYLOAD_V2 = {"sitemap.xml": b"<urlset/>", "index.html": b"v2"}
BROKEN_PAYLOAD = {"index.html": b"no sitemap"}


class MirrorDeployer:
    """A fictional third destination (think rsync to a static host).

    Composing :class:`FilesystemDeployer` as the local store gives
    immutable releases, locking and rollback for free; activation adds
    one step — copying the current release into the mirror directory.
    Nothing in the CMS knows this class exists.
    """

    contract_version = DEPLOY_CONTRACT_VERSION
    capabilities = frozenset({"rollback", "remote"})

    def __init__(self, root: Path, mirror: Path) -> None:
        self._store = FilesystemDeployer(root)
        self._mirror = mirror

    def state(self) -> DeployState:
        return self._store.state()

    def releases(self) -> list[ReleaseInfo]:
        return self._store.releases()

    def record_failure(self, error: str, phase: str, actor: str) -> DeployState:
        return self._store.record_failure(error, phase, actor)

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState:
        state = self._store.deploy(files, digest, actor)
        if state.status == "active":
            self._sync()
        return state

    def rollback(self, release_id: str, actor: str) -> DeployState:
        state = self._store.rollback(release_id, actor)
        if state.status in ("active", "rolled-back"):
            self._sync()
        return state

    def _sync(self) -> None:
        source = (self._store.root / "current").resolve()
        self._mirror.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, self._mirror, dirs_exist_ok=True)


def _mirror_factory(settings: dict[str, str], project_dir: Path) -> MirrorDeployer:
    raw_root = settings.get("root", "")
    raw_mirror = settings.get("mirror_root", "")
    if not raw_root or not raw_mirror:
        raise DeployError("the mirror provider needs [deploy] root and mirror_root")
    root, mirror = Path(raw_root), Path(raw_mirror)
    if not root.is_absolute():
        root = project_dir / root
    if not mirror.is_absolute():
        mirror = project_dir / mirror
    return MirrorDeployer(root, mirror)


extension = Extension(name="mirror-deploy", deploy_providers={"mirror": _mirror_factory})
"""What a real deployment extension ships: a name and a factory."""


@pytest.fixture(params=["filesystem", "swa", "mirror"])
def provider_case(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[str, dict[str, str]]]:
    """Every provider expressed the same way the CMS sees it: a name
    plus the raw ``[deploy]`` settings table."""
    name = str(request.param)
    settings = {"root": str(tmp_path / "store")}
    if name == "mirror":
        register_deploy_provider("mirror", _mirror_factory)  # idempotent
        settings["mirror_root"] = str(tmp_path / "mirror")
    if name == "swa":
        server = socketserver.TCPServer(("127.0.0.1", 0), MockSwa)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        MockSwa.mode = "ok"
        MockSwa.uploads = []
        MockSwa.polls = 0
        MockSwa.base = f"http://127.0.0.1:{server.server_address[1]}"
        monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
        settings["deploy_url"] = f"{MockSwa.base}/deploy"
        yield name, settings
        server.shutdown()
        return
    yield name, settings


def _build(case: tuple[str, dict[str, str]], project_dir: Path) -> DeployProvider:
    name, settings = case
    return create_deploy_provider(name, settings, project_dir)


def test_conformance_declares_the_contract(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    provider = _build(provider_case, tmp_path)
    assert isinstance(provider, DeployProvider)
    assert provider.contract_version == DEPLOY_CONTRACT_VERSION
    assert isinstance(provider.capabilities, frozenset)
    assert provider.capabilities <= {"rollback", "health", "remote"}


def test_conformance_deploy_activates_and_state_survives_instances(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    provider = _build(provider_case, tmp_path)
    state = provider.deploy(dict(PAYLOAD_V1), digest="a" * 16, actor="ana")
    assert state.status == "active"
    assert state.release_id
    assert any(r.release_id == state.release_id for r in provider.releases())
    fresh = _build(provider_case, tmp_path)  # a new process would see the same
    assert fresh.state() == state


def test_conformance_incomplete_payload_never_becomes_active(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    provider = _build(provider_case, tmp_path)
    good = provider.deploy(dict(PAYLOAD_V1), digest="a" * 16, actor="ana")
    state = provider.deploy(dict(BROKEN_PAYLOAD), digest="b" * 16, actor="ana")
    assert state.status == "failed"
    assert state.error
    assert any(r.release_id == good.release_id for r in provider.releases())


def test_conformance_rollback_reactivates_without_rebuild(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    provider = _build(provider_case, tmp_path)
    if "rollback" not in provider.capabilities:
        pytest.skip("provider does not declare rollback")
    first = provider.deploy(dict(PAYLOAD_V1), digest="a" * 16, actor="ana")
    provider.deploy(dict(PAYLOAD_V2), digest="b" * 16, actor="ana")
    state = provider.rollback(first.release_id, actor="maria")
    assert state.status in ("active", "rolled-back")
    assert state.release_id == first.release_id


def test_conformance_concurrent_deploys_are_refused(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    _name, settings = provider_case
    provider = _build(provider_case, tmp_path)
    lock = Path(settings["root"]) / ".deploy.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("held by another deployment", encoding="utf-8")
    try:
        with pytest.raises(DeployLocked):
            provider.deploy(dict(PAYLOAD_V1), digest="a" * 16, actor="ana")
    finally:
        lock.unlink()


def test_conformance_record_failure_keeps_the_releases(
    provider_case: tuple[str, dict[str, str]], tmp_path: Path
) -> None:
    provider = _build(provider_case, tmp_path)
    good = provider.deploy(dict(PAYLOAD_V1), digest="a" * 16, actor="ana")
    state = provider.record_failure("the build exploded", phase="building", actor="ana")
    assert state.status == "failed"
    assert state.error == "the build exploded"
    assert any(r.release_id == good.release_id for r in provider.releases())


# --- the registry itself ---------------------------------------------------


def test_bundled_providers_are_discoverable() -> None:
    names = available_deploy_providers()
    assert "filesystem" in names
    assert "swa" in names


def test_unknown_provider_is_refused_with_the_known_names(tmp_path: Path) -> None:
    with pytest.raises(DeployError, match=r"unknown deploy provider 'ftp'.*filesystem"):
        create_deploy_provider("ftp", {"root": str(tmp_path)}, tmp_path)


def test_contract_version_mismatch_is_refused_at_selection(tmp_path: Path) -> None:
    class AncientDeployer(MirrorDeployer):
        contract_version = 0

    register_deploy_provider(
        "conformance-ancient",
        lambda settings, project_dir: AncientDeployer(tmp_path / "s", tmp_path / "m"),
    )
    with pytest.raises(DeployError, match="contract version 0"):
        create_deploy_provider("conformance-ancient", {}, tmp_path)


def test_non_conforming_object_is_refused_at_selection(tmp_path: Path) -> None:
    class NotADeployer:
        contract_version = DEPLOY_CONTRACT_VERSION
        capabilities: frozenset[str] = frozenset()

    register_deploy_provider("conformance-hollow", lambda settings, project_dir: NotADeployer())
    with pytest.raises(DeployError, match="does not implement the deploy contract"):
        create_deploy_provider("conformance-hollow", {}, tmp_path)


def test_conflicting_reregistration_is_loud() -> None:
    register_deploy_provider("mirror", _mirror_factory)  # same identity: fine
    with pytest.raises(ValueError, match="already registered differently"):
        register_deploy_provider("mirror", lambda settings, project_dir: None)


# --- an extension-shipped provider, end to end -----------------------------


def test_a_third_provider_needs_no_core_change(tmp_path: Path) -> None:
    """An admin publishes to a destination the CMS has never heard of.

    ``sardine.toml`` activates the extension defined in this file and
    selects its provider; the editor, the publish flow and the panel run
    unchanged — the release lands in the mirror directory.
    """
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Live"\nbase_url = "https://live.example"\nlanguages = []\n'
        '\nextensions = ["test_deploy_conformance:extension"]\n'
        "\n[deploy]\n"
        'provider = "mirror"\n'
        f'root = "{tmp_path / "store"}"\n'
        f'mirror_root = "{tmp_path / "mirror"}"\n',
        encoding="utf-8",
    )
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        article = new_article(
            "launch",
            ArticleContent(title="Launch note", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(article)
    app = create_app(
        AdminSettings(
            storage_url=url,
            media_dir=tmp_path / "media",
            project_dir=tmp_path,
            publish_gate=False,
        )
    )
    with TestClient(app, base_url="https://testserver") as client:
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "ana",
                "password": PASSWORD,
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        for target in ("review", "published"):
            client.post(
                "/articles/launch/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
        panel = client.get("/publishing").text
    assert "Publish site now" in panel  # the panel reports an active site
    assert (tmp_path / "mirror" / "sitemap.xml").is_file()
    assert (tmp_path / "mirror" / "blog" / "launch").is_dir()  # the published article arrived
