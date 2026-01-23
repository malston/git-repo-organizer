# ABOUTME: Unit tests for gro workspace operations.
# ABOUTME: Tests scanning, symlink management, and sync planning.
"""Tests for gro.workspace."""

from pathlib import Path

from gro.config import create_default_config
from gro.models import Category, Config, Workspace
from gro.workspace import (
    apply_sync_plan,
    check_symlink_status,
    cleanup_empty_directories,
    create_symlink,
    create_sync_plan,
    get_repo_status,
    get_symlink_path,
    get_symlink_target,
    remove_symlink,
    scan_code_dir,
    scan_workspace_symlinks,
    update_symlink,
)


class TestScanCodeDir:
    """Tests for scan_code_dir function."""

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        assert scan_code_dir(code_path) == []

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        """Nonexistent directory returns empty list."""
        code_path = tmp_path / "nonexistent"
        assert scan_code_dir(code_path) == []

    def test_finds_git_repos(self, tmp_path: Path) -> None:
        """Finds directories containing .git."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        # Create git repos
        (code_path / "repo-a" / ".git").mkdir(parents=True)
        (code_path / "repo-b" / ".git").mkdir(parents=True)

        # Create non-git directory
        (code_path / "not-a-repo").mkdir()

        repos = scan_code_dir(code_path)
        assert repos == ["repo-a", "repo-b"]

    def test_ignores_files(self, tmp_path: Path) -> None:
        """Ignores files in code directory."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        (code_path / "repo" / ".git").mkdir(parents=True)
        (code_path / "somefile.txt").touch()

        repos = scan_code_dir(code_path)
        assert repos == ["repo"]


class TestScanWorkspaceSymlinks:
    """Tests for scan_workspace_symlinks function."""

    def test_empty_workspace(self, tmp_path: Path) -> None:
        """Empty workspace returns empty dict."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        assert scan_workspace_symlinks(workspace_path) == {}

    def test_nonexistent_workspace(self, tmp_path: Path) -> None:
        """Nonexistent workspace returns empty dict."""
        workspace_path = tmp_path / "nonexistent"
        assert scan_workspace_symlinks(workspace_path) == {}

    def test_root_symlinks(self, tmp_path: Path) -> None:
        """Finds symlinks at workspace root."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        target = tmp_path / "target"
        target.mkdir()

        (workspace_path / "link1").symlink_to(target)
        (workspace_path / "link2").symlink_to(target)

        result = scan_workspace_symlinks(workspace_path)
        assert "." in result
        assert sorted(result["."]) == ["link1", "link2"]

    def test_category_symlinks(self, tmp_path: Path) -> None:
        """Finds symlinks in category directories."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        target = tmp_path / "target"
        target.mkdir()

        # Create category with symlinks
        (workspace_path / "vmware").mkdir()
        (workspace_path / "vmware" / "repo1").symlink_to(target)

        (workspace_path / "vmware" / "vsphere").mkdir()
        (workspace_path / "vmware" / "vsphere" / "repo2").symlink_to(target)

        result = scan_workspace_symlinks(workspace_path)
        assert "vmware" in result
        assert result["vmware"] == ["repo1"]
        assert "vmware/vsphere" in result
        assert result["vmware/vsphere"] == ["repo2"]


class TestGetSymlinkPath:
    """Tests for get_symlink_path function."""

    def test_root_category(self) -> None:
        """Root category returns path at workspace root."""
        workspace = Path("/workspace")
        path = get_symlink_path(workspace, ".", "repo")
        assert path == Path("/workspace/repo")

    def test_nested_category(self) -> None:
        """Nested category returns full path."""
        workspace = Path("/workspace")
        path = get_symlink_path(workspace, "vmware/vsphere", "repo")
        assert path == Path("/workspace/vmware/vsphere/repo")


class TestGetSymlinkTarget:
    """Tests for get_symlink_target function."""

    def test_returns_code_path(self) -> None:
        """Returns path in code directory."""
        code_path = Path("/code")
        target = get_symlink_target(code_path, "my-repo")
        assert target == Path("/code/my-repo")


class TestCreateSymlink:
    """Tests for create_symlink function."""

    def test_creates_symlink(self, tmp_path: Path) -> None:
        """Creates symlink pointing to target."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        assert create_symlink(source, target)
        assert source.is_symlink()
        assert source.resolve() == target

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Creates parent directories if needed."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "a" / "b" / "link"
        assert create_symlink(source, target)
        assert source.is_symlink()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't create symlink."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        assert create_symlink(source, target, dry_run=True)
        assert not source.exists()


class TestRemoveSymlink:
    """Tests for remove_symlink function."""

    def test_removes_symlink(self, tmp_path: Path) -> None:
        """Removes existing symlink."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        source.symlink_to(target)

        assert remove_symlink(source)
        assert not source.exists()

    def test_returns_false_for_non_symlink(self, tmp_path: Path) -> None:
        """Returns False for non-symlink."""
        regular_file = tmp_path / "file"
        regular_file.touch()

        assert not remove_symlink(regular_file)
        assert regular_file.exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't remove symlink."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        source.symlink_to(target)

        assert remove_symlink(source, dry_run=True)
        assert source.exists()


class TestUpdateSymlink:
    """Tests for update_symlink function."""

    def test_updates_symlink(self, tmp_path: Path) -> None:
        """Updates symlink to new target."""
        old_target = tmp_path / "old"
        old_target.mkdir()
        new_target = tmp_path / "new"
        new_target.mkdir()

        source = tmp_path / "link"
        source.symlink_to(old_target)

        assert update_symlink(source, new_target)
        assert source.resolve() == new_target

    def test_creates_if_not_exists(self, tmp_path: Path) -> None:
        """Creates symlink if it doesn't exist."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        assert update_symlink(source, target)
        assert source.is_symlink()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't update symlink."""
        old_target = tmp_path / "old"
        old_target.mkdir()
        new_target = tmp_path / "new"
        new_target.mkdir()

        source = tmp_path / "link"
        source.symlink_to(old_target)

        assert update_symlink(source, new_target, dry_run=True)
        assert source.resolve() == old_target


class TestCheckSymlinkStatus:
    """Tests for check_symlink_status function."""

    def test_ok_status(self, tmp_path: Path) -> None:
        """Returns 'ok' for correct symlink."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        source.symlink_to(target)

        assert check_symlink_status(source, target) == "ok"

    def test_missing_status(self, tmp_path: Path) -> None:
        """Returns 'missing' for nonexistent symlink."""
        target = tmp_path / "target"
        source = tmp_path / "link"

        assert check_symlink_status(source, target) == "missing"

    def test_wrong_target_status(self, tmp_path: Path) -> None:
        """Returns 'wrong_target' for wrong symlink target."""
        target1 = tmp_path / "target1"
        target1.mkdir()
        target2 = tmp_path / "target2"
        target2.mkdir()

        source = tmp_path / "link"
        source.symlink_to(target1)

        assert check_symlink_status(source, target2) == "wrong_target"

    def test_not_symlink_status(self, tmp_path: Path) -> None:
        """Returns 'not_symlink' for regular file."""
        target = tmp_path / "target"
        target.mkdir()

        source = tmp_path / "link"
        source.touch()

        assert check_symlink_status(source, target) == "not_symlink"


class TestGetRepoStatus:
    """Tests for get_repo_status function."""

    def test_existing_repo_with_symlinks(self, tmp_path: Path) -> None:
        """Gets status of existing repo with symlinks."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "my-repo").symlink_to(code_path / "my-repo")

        config = Config(code_path=code_path)
        ws = Workspace(path=workspace_path)
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws

        status = get_repo_status(config, "my-repo")
        assert status.name == "my-repo"
        assert status.exists_in_code is True
        assert ("workspace", ".") in status.locations
        assert status.symlink_status[("workspace", ".")] == "ok"

    def test_missing_repo(self, tmp_path: Path) -> None:
        """Gets status of missing repo."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        config = Config(code_path=code_path)
        ws = Workspace(path=tmp_path / "workspace")
        ws.categories["."] = Category(path=".", repos=["missing-repo"])
        config.workspaces["workspace"] = ws

        status = get_repo_status(config, "missing-repo")
        assert status.name == "missing-repo"
        assert status.exists_in_code is False


class TestCreateSyncPlan:
    """Tests for create_sync_plan function."""

    def test_empty_state(self, tmp_path: Path) -> None:
        """Empty config and code produces empty plan."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )

        plan = create_sync_plan(config)
        assert plan.has_changes is False

    def test_new_repos_to_add(self, tmp_path: Path) -> None:
        """Detects repos in code not in config."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "new-repo" / ".git").mkdir(parents=True)

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )

        plan = create_sync_plan(config)
        assert "new-repo" in plan.repos_to_add

    def test_missing_repos(self, tmp_path: Path) -> None:
        """Detects repos in config not in code."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )
        ws = config.workspaces["workspace"]
        ws.categories["."] = Category(path=".", repos=["missing-repo"])

        plan = create_sync_plan(config)
        assert "missing-repo" in plan.repos_missing

    def test_symlinks_to_create(self, tmp_path: Path) -> None:
        """Detects symlinks that need to be created."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )
        ws = config.workspaces["workspace"]
        ws.categories["."] = Category(path=".", repos=["my-repo"])

        plan = create_sync_plan(config)
        assert ("workspace", ".", "my-repo") in plan.symlinks_to_create

    def test_orphaned_symlinks_to_remove(self, tmp_path: Path) -> None:
        """Detects symlinks not in config."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "orphan").symlink_to(code_path)

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )

        plan = create_sync_plan(config)
        assert ("workspace", ".", "orphan") in plan.symlinks_to_remove


class TestApplySyncPlan:
    """Tests for apply_sync_plan function."""

    def test_creates_symlinks(self, tmp_path: Path) -> None:
        """Creates symlinks from plan."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )
        ws = config.workspaces["workspace"]
        ws.categories["."] = Category(path=".", repos=["my-repo"])

        plan = create_sync_plan(config)
        results = apply_sync_plan(config, plan)

        assert len(results["created"]) == 1
        assert (workspace_path / "my-repo").is_symlink()

    def test_removes_orphans_when_requested(self, tmp_path: Path) -> None:
        """Removes orphaned symlinks when remove_orphans=True."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        orphan_link = workspace_path / "orphan"
        orphan_link.symlink_to(code_path)

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )

        plan = create_sync_plan(config)
        results = apply_sync_plan(config, plan, remove_orphans=True)

        assert len(results["removed"]) == 1
        assert not orphan_link.exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't make changes."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        config = create_default_config(
            code_path=code_path,
            workspace_paths=[workspace_path],
        )
        ws = config.workspaces["workspace"]
        ws.categories["."] = Category(path=".", repos=["my-repo"])

        plan = create_sync_plan(config)
        results = apply_sync_plan(config, plan, dry_run=True)

        assert len(results["created"]) == 1
        assert not (workspace_path / "my-repo").exists()


class TestCleanupEmptyDirectories:
    """Tests for cleanup_empty_directories function."""

    def test_removes_empty_dirs(self, tmp_path: Path) -> None:
        """Removes empty directories."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "empty" / "nested").mkdir(parents=True)

        removed = cleanup_empty_directories(workspace_path)
        assert len(removed) == 2
        assert not (workspace_path / "empty").exists()

    def test_preserves_workspace_root(self, tmp_path: Path) -> None:
        """Does not remove workspace root."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()

        removed = cleanup_empty_directories(workspace_path)
        assert len(removed) == 0
        assert workspace_path.exists()

    def test_preserves_non_empty_dirs(self, tmp_path: Path) -> None:
        """Preserves directories with content."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "has-file").mkdir()
        (workspace_path / "has-file" / "file.txt").touch()

        removed = cleanup_empty_directories(workspace_path)
        assert len(removed) == 0
        assert (workspace_path / "has-file").exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't remove directories."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "empty").mkdir()

        removed = cleanup_empty_directories(workspace_path, dry_run=True)
        assert len(removed) == 1
        assert (workspace_path / "empty").exists()
