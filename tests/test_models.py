# ABOUTME: Unit tests for gro data models.
# ABOUTME: Tests Config, Workspace, Category, and related classes.
"""Tests for gro.models."""

from pathlib import Path

from gro.models import Category, Config, RepoStatus, SyncPlan, Workspace


class TestCategory:
    """Tests for Category dataclass."""

    def test_is_root_true(self) -> None:
        """Root category has path '.'."""
        cat = Category(path=".", repos=["foo"])
        assert cat.is_root is True

    def test_is_root_false(self) -> None:
        """Non-root category has different path."""
        cat = Category(path="vmware/vsphere", repos=["foo"])
        assert cat.is_root is False


class TestWorkspace:
    """Tests for Workspace dataclass."""

    def test_name(self) -> None:
        """Name is basename of path."""
        ws = Workspace(path=Path("/home/user/workspace"))
        assert ws.name == "workspace"

    def test_get_category(self) -> None:
        """Get category by path."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["vmware"] = Category(path="vmware", repos=["foo"])
        assert ws.get_category("vmware") is not None
        assert ws.get_category("nonexistent") is None

    def test_get_or_create_category(self) -> None:
        """Get or create category."""
        ws = Workspace(path=Path("/workspace"))
        cat = ws.get_or_create_category("vmware")
        assert cat.path == "vmware"
        assert "vmware" in ws.categories

        # Getting again returns same instance
        cat2 = ws.get_or_create_category("vmware")
        assert cat2 is cat

    def test_all_repos(self) -> None:
        """Get all repos across categories."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["cat1"] = Category(path="cat1", repos=["a", "b"])
        ws.categories["cat2"] = Category(path="cat2", repos=["b", "c"])
        assert ws.all_repos() == {"a", "b", "c"}

    def test_find_repo_categories(self) -> None:
        """Find categories containing a repo."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["cat1"] = Category(path="cat1", repos=["a", "b"])
        ws.categories["cat2"] = Category(path="cat2", repos=["b", "c"])
        assert ws.find_repo_categories("b") == ["cat1", "cat2"]
        assert ws.find_repo_categories("a") == ["cat1"]
        assert ws.find_repo_categories("x") == []


class TestConfig:
    """Tests for Config dataclass."""

    def test_all_repos(self) -> None:
        """Get all repos across all workspaces."""
        config = Config(code_path=Path("/code"))
        ws1 = Workspace(path=Path("/ws1"))
        ws1.categories["cat1"] = Category(path="cat1", repos=["a", "b"])
        ws2 = Workspace(path=Path("/ws2"))
        ws2.categories["cat2"] = Category(path="cat2", repos=["b", "c"])
        config.workspaces = {"ws1": ws1, "ws2": ws2}

        assert config.all_repos() == {"a", "b", "c"}

    def test_find_repo_locations(self) -> None:
        """Find all locations of a repo."""
        config = Config(code_path=Path("/code"))
        ws1 = Workspace(path=Path("/ws1"))
        ws1.categories["cat1"] = Category(path="cat1", repos=["a"])
        ws2 = Workspace(path=Path("/ws2"))
        ws2.categories["cat2"] = Category(path="cat2", repos=["a"])
        config.workspaces = {"ws1": ws1, "ws2": ws2}

        locations = config.find_repo_locations("a")
        assert ("ws1", "cat1") in locations
        assert ("ws2", "cat2") in locations


class TestRepoStatus:
    """Tests for RepoStatus dataclass."""

    def test_is_orphaned(self) -> None:
        """Orphaned repo exists but has no locations."""
        status = RepoStatus(name="foo", exists_in_code=True, locations=[])
        assert status.is_orphaned is True

        status2 = RepoStatus(name="foo", exists_in_code=True, locations=[("ws", "cat")])
        assert status2.is_orphaned is False

    def test_is_missing(self) -> None:
        """Missing repo is configured but doesn't exist."""
        status = RepoStatus(name="foo", exists_in_code=False, locations=[("ws", "cat")])
        assert status.is_missing is True

        status2 = RepoStatus(name="foo", exists_in_code=True, locations=[("ws", "cat")])
        assert status2.is_missing is False


class TestSyncPlan:
    """Tests for SyncPlan dataclass."""

    def test_has_changes_empty(self) -> None:
        """Empty plan has no changes."""
        plan = SyncPlan(
            repos_to_add=[],
            repos_missing=[],
            symlinks_to_create=[],
            symlinks_to_update=[],
            symlinks_to_remove=[],
        )
        assert plan.has_changes is False

    def test_has_changes_with_additions(self) -> None:
        """Plan with additions has changes."""
        plan = SyncPlan(
            repos_to_add=["foo"],
            repos_missing=[],
            symlinks_to_create=[],
            symlinks_to_update=[],
            symlinks_to_remove=[],
        )
        assert plan.has_changes is True
