"""The filesystem deployment provider (#156 slice 1): the rules, not
the happy path — a failure never removes the healthy version."""

from pathlib import Path

import pytest
from cms_build.deploy import DeployLocked, DeployState, FilesystemDeployer

SITE_A = {
    "index.html": b"<h1>version A</h1>",
    "sitemap.xml": b"<urlset/>",
    "about/index.html": b"about A",
}
SITE_B = {"index.html": b"<h1>version B</h1>", "sitemap.xml": b"<urlset/>"}
BROKEN = {"not-index.txt": b"no entry point"}


def test_deploy_activates_and_republishing_keeps_the_previous(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    first = deployer.deploy(SITE_A, digest="a" * 16, actor="ana")
    assert first.status == "active"
    assert (tmp_path / "current" / "index.html").read_bytes() == SITE_A["index.html"]

    second = deployer.deploy(SITE_B, digest="b" * 16, actor="ana")
    assert second.status == "active"
    assert (tmp_path / "current" / "index.html").read_bytes() == SITE_B["index.html"]
    releases = deployer.releases()
    assert len(releases) == 2  # the previous release is kept
    assert sum(1 for release in releases if release.active) == 1


def test_a_broken_release_never_touches_the_live_site(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    deployer.deploy(SITE_A, digest="a" * 16, actor="ana")
    state = deployer.deploy(BROKEN, digest="c" * 16, actor="ana")
    assert state.status == "failed" and "sitemap.xml" in state.error
    # the healthy version still serves
    assert (tmp_path / "current" / "index.html").read_bytes() == SITE_A["index.html"]
    assert deployer.state().status == "failed"  # the panel sees the truth


def test_failed_health_check_rolls_back_automatically(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path, health_url="http://127.0.0.1:1/nothing-there")
    # first deploy: health fails and there is nothing to roll back to
    first = deployer.deploy(SITE_A, digest="a" * 16, actor="ana")
    assert first.status == "failed" and first.phase == "health"

    healthy = FilesystemDeployer(tmp_path)
    healthy.deploy(SITE_A, digest="a" * 16, actor="ana")
    failing = FilesystemDeployer(tmp_path, health_url="http://127.0.0.1:1/nothing-there")
    state = failing.deploy(SITE_B, digest="b" * 16, actor="ana")
    assert state.status == "rolled-back" and state.phase == "health"
    assert (tmp_path / "current" / "index.html").read_bytes() == SITE_A["index.html"]


def test_manual_rollback_needs_no_rebuild(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    first = deployer.deploy(SITE_A, digest="a" * 16, actor="ana")
    deployer.deploy(SITE_B, digest="b" * 16, actor="ana")
    state = deployer.rollback(first.release_id, actor="maria")
    assert state.status == "active" and state.release_id == first.release_id
    assert (tmp_path / "current" / "index.html").read_bytes() == SITE_A["index.html"]


def test_concurrent_deployments_are_refused(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    deployer._acquire_lock()
    try:
        with pytest.raises(DeployLocked):
            deployer.deploy(SITE_A, digest="a" * 16, actor="ana")
    finally:
        deployer._release_lock()
    # and the lock releases cleanly afterwards
    assert deployer.deploy(SITE_A, digest="a" * 16, actor="ana").status == "active"


def test_prune_keeps_active_and_previous(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path, keep=2)
    for index in range(5):
        deployer.deploy(
            {"index.html": f"v{index}".encode(), "sitemap.xml": b"<urlset/>"},
            digest=f"{index}" * 16,
            actor="ana",
        )
    releases = deployer.releases()
    assert len(releases) <= 3  # keep + the previous safety margin
    assert any(release.active for release in releases)


def test_state_survives_processes(tmp_path: Path) -> None:
    FilesystemDeployer(tmp_path).deploy(SITE_A, digest="a" * 16, actor="ana")
    fresh = FilesystemDeployer(tmp_path)
    assert fresh.state().status == "active"
    assert isinstance(fresh.state(), DeployState)
