"""The filesystem deployment provider (#156, slice 1): rules, not hopes."""

from pathlib import Path

import pytest
from cms_build.deploy import DeployLocked, FilesystemDeployer


def _site(tag: str) -> dict[str, bytes]:
    return {
        "index.html": f"<h1>release {tag}</h1>".encode(),
        "blog/index.html": f"<h1>blog {tag}</h1>".encode(),
        "sitemap.xml": b"<urlset/>",  # the filesystem health marker
    }


def test_deploy_activates_atomically_and_keeps_history(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    first = deployer.deploy(_site("one"), digest="a" * 64, actor="ana")
    assert first.status == "active"
    assert (tmp_path / "current" / "index.html").read_bytes() == b"<h1>release one</h1>"

    second = deployer.deploy(_site("two"), digest="b" * 64, actor="ana")
    assert second.status == "active"
    assert (tmp_path / "current" / "index.html").read_bytes() == b"<h1>release two</h1>"
    releases = deployer.releases()
    assert len(releases) == 2
    assert releases[0].active and not releases[1].active


def test_failure_before_activation_leaves_the_healthy_version(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    deployer.deploy(_site("healthy"), digest="a" * 64, actor="ana")
    broken = {"not-a-build.txt": b"missing everything"}
    state = deployer.deploy(broken, digest="c" * 64, actor="ana")
    assert state.status == "failed" and "sitemap.xml" in state.error
    assert (tmp_path / "current" / "index.html").read_bytes() == b"<h1>release healthy</h1>"


def test_failed_health_check_rolls_back_automatically(tmp_path: Path) -> None:
    # A closed port: the URL check must fail after activation.
    deployer = FilesystemDeployer(tmp_path, health_url="http://127.0.0.1:9/health")
    no_url = FilesystemDeployer(tmp_path)
    no_url.deploy(_site("good"), digest="a" * 64, actor="ana")
    state = deployer.deploy(_site("bad"), digest="d" * 64, actor="ana")
    assert state.status == "rolled-back"
    assert "previous release reactivated" in state.error
    assert (tmp_path / "current" / "index.html").read_bytes() == b"<h1>release good</h1>"


def test_manual_rollback_needs_no_rebuild(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    deployer.deploy(_site("one"), digest="a" * 64, actor="ana")
    older = deployer.releases()[0].release_id
    deployer.deploy(_site("two"), digest="b" * 64, actor="ana")
    state = deployer.rollback(older, actor="maria")
    assert state.status == "active" and state.release_id == older
    assert (tmp_path / "current" / "index.html").read_bytes() == b"<h1>release one</h1>"


def test_concurrent_deployments_are_refused(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path)
    deployer._acquire_lock()
    with pytest.raises(DeployLocked):
        deployer.deploy(_site("late"), digest="e" * 64, actor="ana")
    deployer._release_lock()
    assert deployer.deploy(_site("late"), digest="e" * 64, actor="ana").status == "active"


def test_pruning_keeps_the_window_and_the_active(tmp_path: Path) -> None:
    deployer = FilesystemDeployer(tmp_path, keep=2)
    for index in range(4):
        deployer.deploy(_site(str(index)), digest=str(index) * 64, actor="ana")
    releases = deployer.releases()
    assert len(releases) <= 3  # keep window + previous safety
    assert releases[0].active
