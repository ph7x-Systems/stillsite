"""Deployment providers (#156): immutable releases, atomic activation.

The contract every provider follows — slice 1 ships the filesystem
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
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

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
    """The generic contract (#156). Slice 1: filesystem; later slices
    implement remote destinations against the same surface."""

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState: ...

    def record_failure(self, error: str, phase: str, actor: str) -> DeployState: ...

    def rollback(self, release_id: str, actor: str) -> DeployState: ...

    def state(self) -> DeployState: ...

    def releases(self) -> list[ReleaseInfo]: ...


class FilesystemDeployer:
    """The local reference provider: versioned releases + symlink."""

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
            release_id = f"{now.strftime('%Y%m%d%H%M%S')}-{digest[:8]}"
            release_dir = self._releases_dir / release_id
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
                    # every complete build emits a sitemap; its absence
                    # means a broken or empty payload, never a real site
                    raise DeployError("the release has no sitemap.xml — not a complete build")
            except DeployError:
                raise
            except OSError as error:
                raise DeployError(f"writing the release failed: {error}") from error

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
