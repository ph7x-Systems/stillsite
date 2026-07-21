"""Deployment providers (#156): immutable releases, atomic activation.

The contract every provider follows; the bundled filesystem
reference implementation (Sardine and the web server share a machine;
Nginx serves ``current/`` and is never touched by a publication):

    releases/<release-id>/site/      the immutable artifact
    releases/<release-id>/release.json   metadata, never served
    current -> releases/<release-id>/site    atomic symlink
    state.json                       provider state for the panel
    .deploy.lock                     cross-process concurrency guard

Rules encoded here, not hoped for: activation is a symlink swap via
rename (atomic on POSIX); a failure before activation leaves the
healthy version untouched; a failed health check after activation
rolls back automatically; rollback reactivates a kept release without
any rebuild; secrets never appear anywhere in this module because the
filesystem provider needs none.
"""

import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

DEPLOY_CONTRACT_VERSION = 1
"""The provider contract's version. A provider declares the version it
implements; a mismatch refuses loudly at selection time, never at
deploy time."""

LOCK_STALE_SECONDS = 600
HEALTH_TIMEOUT_SECONDS = 5


class DeployError(Exception):
    """A deployment problem with an operator-actionable message."""


class DeployLocked(DeployError):
    """Another deployment is already running."""


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    release_id: str
    digest: str
    at: str
    actor: str
    active: bool = False


@dataclass(frozen=True, slots=True)
class DeployState:
    status: str
    """``active`` | ``failed`` | ``rolled-back`` | ``never-deployed``."""
    release_id: str = ""
    at: str = ""
    actor: str = ""
    error: str = ""
    phase: str = ""
    """Where a failure happened: ``building`` | ``deploying`` | ``health``."""


@runtime_checkable
class DeployProvider(Protocol):
    """The generic contract (#156). Implementing it is the whole job of
    adding a destination — the editor, the editorial flow and the
    publication pipeline never change."""

    contract_version: int
    capabilities: frozenset[str]
    """What the provider genuinely supports: ``rollback``, ``health``,
    ``remote``. The panel adapts; nothing else may assume more."""

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState: ...

    def record_failure(self, error: str, phase: str, actor: str) -> DeployState: ...

    def rollback(self, release_id: str, actor: str) -> DeployState: ...

    def state(self) -> DeployState: ...

    def releases(self) -> list[ReleaseInfo]: ...


_PROVIDERS: dict[str, object] = {}


def register_deploy_provider(name: str, factory: object) -> None:
    """Register a provider factory ``(settings: dict[str, str],
    project_dir: Path) -> DeployProvider``. Idempotent by identity;
    loud on a conflicting re-registration — a configured name must
    never resolve to something unexpected."""
    existing = _PROVIDERS.get(name)
    if existing is not None and existing is not factory:
        raise ValueError(f"deploy provider {name!r} is already registered differently")
    _PROVIDERS[name] = factory


def available_deploy_providers() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


def create_deploy_provider(
    name: str, settings: dict[str, str], project_dir: Path
) -> DeployProvider:
    """Resolve and build the configured provider, validating the
    contract version before anything runs."""
    factory = _PROVIDERS.get(name)
    if factory is None:
        known = ", ".join(available_deploy_providers()) or "none"
        raise DeployError(f"unknown deploy provider {name!r} (registered: {known})")
    provider = factory(settings, project_dir)  # type: ignore[operator]
    version = getattr(provider, "contract_version", None)
    if version != DEPLOY_CONTRACT_VERSION:
        raise DeployError(
            f"provider {name!r} implements contract version {version!r}; "
            f"this CMS speaks version {DEPLOY_CONTRACT_VERSION}"
        )
    if not isinstance(provider, DeployProvider):
        raise DeployError(f"provider {name!r} does not implement the deploy contract")
    return provider


def write_release(
    releases_dir: Path, files: dict[str, bytes], digest: str, actor: str, now: datetime
) -> tuple[str, Path]:
    """Write an immutable release; refuse incomplete payloads. Shared by
    every provider — remote ones keep the same local store, which is
    what makes rollback-without-rebuild possible anywhere."""
    release_id = f"{now.strftime('%Y%m%d%H%M%S')}-{digest[:8]}"
    release_dir = releases_dir / release_id
    try:
        site_dir = release_dir / "site"
        for path, data in files.items():
            target = site_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (release_dir / "release.json").write_text(
            json.dumps(
                {
                    "release_id": release_id,
                    "digest": digest,
                    "at": now.isoformat(),
                    "actor": actor,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        if not (site_dir / "sitemap.xml").is_file():
            # every complete build emits a sitemap; its absence means a
            # broken or empty payload, never a real site
            raise DeployError("the release has no sitemap.xml — not a complete build")
    except DeployError:
        raise
    except OSError as error:
        raise DeployError(f"writing the release failed: {error}") from error
    return release_id, site_dir


class FilesystemDeployer:
    """The local reference provider: versioned releases + symlink."""

    contract_version = DEPLOY_CONTRACT_VERSION
    capabilities = frozenset({"rollback", "health"})

    def __init__(self, root: Path, health_url: str = "", keep: int = 5) -> None:
        self.root = root
        self.health_url = health_url
        self.keep = max(keep, 1)

    # --- layout ----------------------------------------------------------

    @property
    def _releases_dir(self) -> Path:
        return self.root / "releases"

    @property
    def _current(self) -> Path:
        return self.root / "current"

    @property
    def _state_file(self) -> Path:
        return self.root / "state.json"

    @property
    def _lock_file(self) -> Path:
        return self.root / ".deploy.lock"

    # --- locking ---------------------------------------------------------

    def _acquire_lock(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            handle = os.open(self._lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age = datetime.now(tz=UTC).timestamp() - self._lock_file.stat().st_mtime
            if age < LOCK_STALE_SECONDS:
                raise DeployLocked("a deployment is already running") from None
            self._lock_file.unlink(missing_ok=True)
            return self._acquire_lock()
        with os.fdopen(handle, "w", encoding="utf-8") as lock:
            lock.write(f"{os.getpid()} {datetime.now(tz=UTC).isoformat()}")
        return None

    def _release_lock(self) -> None:
        self._lock_file.unlink(missing_ok=True)

    # --- state -----------------------------------------------------------

    def _write_state(self, state: DeployState) -> DeployState:
        payload = json.dumps(asdict(state), ensure_ascii=False, sort_keys=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=self.root, delete=False, encoding="utf-8"
        ) as handle:
            handle.write(payload)
        os.replace(handle.name, self._state_file)
        return state

    def state(self) -> DeployState:
        if not self._state_file.is_file():
            return DeployState(status="never-deployed")
        data = json.loads(self._state_file.read_text(encoding="utf-8"))
        return DeployState(**data)

    def releases(self) -> list[ReleaseInfo]:
        if not self._releases_dir.is_dir():
            return []
        active = self._active_release_id()
        found = []
        for marker in sorted(self._releases_dir.glob("*/release.json"), reverse=True):
            data = json.loads(marker.read_text(encoding="utf-8"))
            found.append(ReleaseInfo(**data, active=data["release_id"] == active))
        return found

    def _active_release_id(self) -> str:
        if not self._current.is_symlink():
            return ""
        return self._current.resolve().parent.name

    # --- the flows -------------------------------------------------------

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState:
        self._acquire_lock()
        try:
            previous = self._active_release_id()
            now = datetime.now(tz=UTC)
            release_id, site_dir = write_release(self._releases_dir, files, digest, actor, now)

            self._activate(site_dir)
            if not self._healthy():
                if previous:
                    self._activate(self._releases_dir / previous / "site")
                    state = DeployState(
                        status="rolled-back",
                        release_id=previous,
                        at=now.isoformat(),
                        actor=actor,
                        error="health check failed — previous release reactivated",
                        phase="health",
                    )
                else:
                    state = DeployState(
                        status="failed",
                        at=now.isoformat(),
                        actor=actor,
                        error="health check failed and no previous release exists",
                        phase="health",
                    )
                return self._write_state(state)
            self._prune(keep_also=previous)
            return self._write_state(
                DeployState(status="active", release_id=release_id, at=now.isoformat(), actor=actor)
            )
        except DeployLocked:
            raise
        except DeployError as error:
            return self._write_state(
                DeployState(
                    status="failed",
                    release_id=self._active_release_id(),
                    at=datetime.now(tz=UTC).isoformat(),
                    actor=actor,
                    error=str(error),
                    phase="deploying",
                )
            )
        finally:
            self._release_lock()

    def record_failure(self, error: str, phase: str, actor: str) -> DeployState:
        """A failure before the provider ran (validation, build): the
        panel shows one truth, the live site stays untouched."""
        return self._write_state(
            DeployState(
                status="failed",
                release_id=self._active_release_id(),
                at=datetime.now(tz=UTC).isoformat(),
                actor=actor,
                error=error,
                phase=phase,
            )
        )

    def mark_failed(self, actor: str, error: str, phase: str) -> DeployState:
        """Record an attempt that failed before any release was written
        (e.g. validation) — the active release stays untouched."""
        return self._write_state(
            DeployState(
                status="failed",
                release_id=self._active_release_id(),
                at=datetime.now(tz=UTC).isoformat(),
                actor=actor,
                error=error,
                phase=phase,
            )
        )

    def rollback(self, release_id: str, actor: str) -> DeployState:
        self._acquire_lock()
        try:
            site_dir = self._releases_dir / release_id / "site"
            if not site_dir.is_dir():
                raise DeployError(f"release {release_id!r} is not kept here")
            self._activate(site_dir)
            now = datetime.now(tz=UTC)
            if not self._healthy():
                return self._write_state(
                    DeployState(
                        status="failed",
                        release_id=release_id,
                        at=now.isoformat(),
                        actor=actor,
                        error="health check failed after rollback",
                        phase="health",
                    )
                )
            return self._write_state(
                DeployState(status="active", release_id=release_id, at=now.isoformat(), actor=actor)
            )
        finally:
            self._release_lock()

    # --- pieces ----------------------------------------------------------

    def _activate(self, site_dir: Path) -> None:
        """Atomic: build the symlink aside, then rename over ``current``."""
        staging = self.root / ".current.staging"
        staging.unlink(missing_ok=True)
        staging.symlink_to(site_dir)
        os.replace(staging, self._current)

    def _healthy(self) -> bool:
        marker = self._current / "sitemap.xml"
        if not (self._current.is_symlink() and marker.is_file()):
            return False
        if not self.health_url:
            return True
        if not self.health_url.startswith(("http://", "https://")):
            return False
        try:
            with urllib.request.urlopen(  # nosec B310 - scheme checked above
                self.health_url, timeout=HEALTH_TIMEOUT_SECONDS
            ) as response:
                return bool(200 <= response.status < 300)
        except OSError:
            return False

    def _prune(self, keep_also: str) -> None:
        active = self._active_release_id()
        kept = 0
        for marker in sorted(self._releases_dir.glob("*/release.json"), reverse=True):
            release_id = marker.parent.name
            kept += 1
            if kept <= self.keep or release_id in (active, keep_also):
                continue
            shutil.rmtree(marker.parent, ignore_errors=True)


TOKEN_ENV = "SARDINE_SWA_DEPLOY_TOKEN"  # nosec B105 - an env var name, not a secret
POLL_INTERVAL_SECONDS = 2.0


class SwaDeployer:
    """Azure Static Web Apps provider (#156): the same contract,
    a remote activation.

    The local release store is identical to the filesystem provider's —
    that is what makes rollback-without-rebuild possible on a remote
    destination. Activation is transport: the release is packed and sent
    to the configured deployment endpoint with a bearer token read from
    the environment at deploy time. The token is never stored, never
    logged, never audited, never part of any error message — it travels
    in one request header and nowhere else. A failure at any phase
    leaves the previously published version serving: the host keeps its
    last successful deployment until a new one succeeds.
    """

    contract_version = DEPLOY_CONTRACT_VERSION
    capabilities = frozenset({"rollback", "health", "remote"})

    def __init__(
        self,
        root: Path,
        deploy_url: str,
        health_url: str = "",
        keep: int = 5,
        timeout: int = 300,
        token_env: str = TOKEN_ENV,
    ) -> None:
        self._store = FilesystemDeployer(root, health_url="", keep=keep)
        self.deploy_url = deploy_url
        self.health_url = health_url
        self.timeout = max(int(timeout), 5)
        self.token_env = token_env

    # The read surface delegates to the shared store.

    def state(self) -> DeployState:
        return self._store.state()

    def releases(self) -> list[ReleaseInfo]:
        return self._store.releases()

    def record_failure(self, error: str, phase: str, actor: str) -> DeployState:
        return self._store.record_failure(error, phase, actor)

    # Flows

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState:
        self._store._acquire_lock()
        now = datetime.now(tz=UTC)
        try:
            self._phase("queued", actor, now)
            try:
                release_id, site_dir = write_release(
                    self._store._releases_dir, files, digest, actor, now
                )
            except DeployError as error:
                return self._store.record_failure(str(error), "building", actor)
            return self._transport(release_id, site_dir, actor)
        finally:
            self._store._release_lock()

    def rollback(self, release_id: str, actor: str) -> DeployState:
        """Re-send a kept release — no rebuild anywhere."""
        self._store._acquire_lock()
        try:
            site_dir = self._store._releases_dir / release_id / "site"
            if not site_dir.is_dir():
                raise DeployError(f"release {release_id!r} is not kept here")
            return self._transport(release_id, site_dir, actor)
        finally:
            self._store._release_lock()

    # Pieces

    def _phase(self, phase: str, actor: str, now: datetime, release_id: str = "") -> None:
        self._store._write_state(
            DeployState(
                status=phase,
                release_id=release_id,
                at=now.isoformat(),
                actor=actor,
                phase=phase,
            )
        )

    def _transport(self, release_id: str, site_dir: Path, actor: str) -> DeployState:
        import io
        import tarfile
        import time

        now = datetime.now(tz=UTC)
        token = os.environ.get(self.token_env, "")
        if not token:
            return self._store.record_failure(
                f"deployment token missing — set {self.token_env}", "uploading", actor
            )

        self._phase("uploading", actor, now, release_id)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            archive.add(site_dir, arcname=".")
        payload = buffer.getvalue()

        request = urllib.request.Request(
            self.deploy_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/gzip",
                "X-Release-Id": release_id,
            },
        )
        if not self.deploy_url.startswith(("http://", "https://")):
            return self._store.record_failure("deploy_url must be http(s)", "uploading", actor)
        try:
            with urllib.request.urlopen(  # nosec B310 - scheme checked above
                request, timeout=self.timeout
            ) as response:
                status_url = response.headers.get("Location", "")
                body = response.read(65536).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                message = "deployment token rejected by the endpoint"
            else:
                message = f"the endpoint answered HTTP {error.code}"
            return self._store.record_failure(message, "uploading", actor)
        except OSError:
            return self._store.record_failure(
                "upload failed — endpoint unreachable or timed out", "uploading", actor
            )

        self._phase("waiting", actor, now, release_id)
        deadline = time.monotonic() + self.timeout
        remote_status = self._parse_status(body)
        while remote_status not in ("succeeded", "failed") and status_url:
            if time.monotonic() > deadline:
                return self._store.record_failure(
                    f"timed out after {self.timeout}s waiting for the deployment",
                    "waiting",
                    actor,
                )
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                with urllib.request.urlopen(  # nosec B310 - same-origin status URL
                    urllib.request.Request(
                        status_url, headers={"Authorization": f"Bearer {token}"}
                    ),
                    timeout=self.timeout,
                ) as response:
                    remote_status = self._parse_status(
                        response.read(65536).decode("utf-8", errors="replace")
                    )
            except OSError:
                return self._store.record_failure(
                    "lost contact with the deployment endpoint", "waiting", actor
                )
        if remote_status == "failed":
            return self._store.record_failure(
                "the endpoint rejected the deployment", "waiting", actor
            )

        self._phase("verifying", actor, now, release_id)
        if self.health_url and not self._healthy():
            return self._store.record_failure(
                "health check failed — the previous publication remains live",
                "health",
                actor,
            )
        self._store._prune(keep_also=release_id)
        return self._store._write_state(
            DeployState(status="active", release_id=release_id, at=now.isoformat(), actor=actor)
        )

    @staticmethod
    def _parse_status(body: str) -> str:
        try:
            data = json.loads(body or "{}")
        except ValueError:
            return ""
        return str(data.get("status", ""))

    def _healthy(self) -> bool:
        if not self.health_url.startswith(("http://", "https://")):
            return False
        try:
            with urllib.request.urlopen(  # nosec B310 - scheme checked above
                self.health_url, timeout=HEALTH_TIMEOUT_SECONDS
            ) as response:
                return bool(200 <= response.status < 300)
        except OSError:
            return False


def _filesystem_factory(settings: dict[str, str], project_dir: Path) -> FilesystemDeployer:
    raw_root = settings.get("root", "")
    if not raw_root:
        raise DeployError("the filesystem provider needs [deploy] root")
    root = Path(raw_root)
    if not root.is_absolute():
        root = project_dir / root
    return FilesystemDeployer(
        root,
        health_url=settings.get("health_url", ""),
        keep=int(settings.get("keep", "5")),
    )


def _swa_factory(settings: dict[str, str], project_dir: Path) -> SwaDeployer:
    raw_root = settings.get("root", "")
    deploy_url = settings.get("deploy_url", "")
    if not raw_root:
        raise DeployError("the swa provider needs [deploy] root (the local release store)")
    if not deploy_url:
        raise DeployError("the swa provider needs [deploy] deploy_url")
    root = Path(raw_root)
    if not root.is_absolute():
        root = project_dir / root
    return SwaDeployer(
        root,
        deploy_url=deploy_url,
        health_url=settings.get("health_url", ""),
        keep=int(settings.get("keep", "5")),
        timeout=int(settings.get("timeout", "300")),
    )


register_deploy_provider("filesystem", _filesystem_factory)
register_deploy_provider("swa", _swa_factory)
