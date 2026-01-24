# ABOUTME: Unit tests for gro data models.
# ABOUTME: Tests Config, Workspace, Category, and related classes.
"""Tests for gro.models."""

from pathlib import Path

from gro.models import Category, Config, RepoEntry, RepoStatus, SyncPlan, Workspace


class TestRepoEntry:
    """Tests for RepoEntry dataclass."""

    def test_from_string_simple(self) -> None:
        """Parse string without alias."""
        entry = RepoEntry.from_string("my-repo")
        assert entry.repo_name == "my-repo"
        assert entry.alias is None

    def test_from_string_with_alias(self) -> None:
        """Parse string with alias."""
        entry = RepoEntry.from_string("acme-git:git")
        assert entry.repo_name == "acme-git"
        assert entry.alias == "git"

    def test_symlink_name_no_alias(self) -> None:
        """symlink_name returns repo_name when no alias."""
        entry = RepoEntry(repo_name="my-repo")
        assert entry.symlink_name == "my-repo"

    def test_symlink_name_with_alias(self) -> None:
        """symlink_name returns alias when set."""
        entry = RepoEntry(repo_name="acme-git", alias="git")
        assert entry.symlink_name == "git"

    def test_to_string_no_alias(self) -> None:
        """to_string returns repo_name when no alias."""
        entry = RepoEntry(repo_name="my-repo")
        assert entry.to_string() == "my-repo"

    def test_to_string_with_alias(self) -> None:
        """to_string returns repo:alias format when aliased."""
        entry = RepoEntry(repo_name="acme-git", alias="git")
        assert entry.to_string() == "acme-git:git"

    def test_roundtrip(self) -> None:
        """Parsing and serializing returns original string."""
        original = "acme-stuff:stuff"
        entry = RepoEntry.from_string(original)
        assert entry.to_string() == original

    def test_roundtrip_no_alias(self) -> None:
        """Parsing and serializing simple repo returns original."""
        original = "govc"
        entry = RepoEntry.from_string(original)
        assert entry.to_string() == original


class TestCategory:
    """Tests for Category dataclass."""

    def test_is_root_true(self) -> None:
        """Root category has path '.'."""
        cat = Category(path=".", entries=[RepoEntry(repo_name="foo")])
        assert cat.is_root is True

    def test_is_root_false(self) -> None:
        """Non-root category has different path."""
        cat = Category(path="vmware/vsphere", entries=[RepoEntry(repo_name="foo")])
        assert cat.is_root is False

    def test_repo_names_simple(self) -> None:
        """repo_names returns set of repo names."""
        cat = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="repo-a"),
                RepoEntry(repo_name="repo-b"),
            ],
        )
        assert cat.repo_names == {"repo-a", "repo-b"}

    def test_repo_names_with_aliases(self) -> None:
        """repo_names returns actual repo names, not aliases."""
        cat = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="acme-git", alias="git"),
                RepoEntry(repo_name="govc"),
            ],
        )
        assert cat.repo_names == {"acme-git", "govc"}

    def test_symlink_names_simple(self) -> None:
        """symlink_names returns set of symlink names (repo names when no alias)."""
        cat = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="repo-a"),
                RepoEntry(repo_name="repo-b"),
            ],
        )
        assert cat.symlink_names == {"repo-a", "repo-b"}

    def test_symlink_names_with_aliases(self) -> None:
        """symlink_names returns aliases when set."""
        cat = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="acme-git", alias="git"),
                RepoEntry(repo_name="acme-stuff", alias="stuff"),
                RepoEntry(repo_name="govc"),
            ],
        )
        assert cat.symlink_names == {"git", "stuff", "govc"}


class TestWorkspace:
    """Tests for Workspace dataclass."""

    def test_name(self) -> None:
        """Name is basename of path."""
        ws = Workspace(path=Path("/home/user/workspace"))
        assert ws.name == "workspace"

    def test_get_category(self) -> None:
        """Get category by path."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["vmware"] = Category(
            path="vmware", entries=[RepoEntry(repo_name="foo")]
        )
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
        ws.categories["cat1"] = Category(
            path="cat1",
            entries=[RepoEntry(repo_name="a"), RepoEntry(repo_name="b")],
        )
        ws.categories["cat2"] = Category(
            path="cat2",
            entries=[RepoEntry(repo_name="b"), RepoEntry(repo_name="c")],
        )
        assert ws.all_repos() == {"a", "b", "c"}

    def test_all_repos_with_aliases(self) -> None:
        """all_repos returns actual repo names, not aliases."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["cat1"] = Category(
            path="cat1",
            entries=[
                RepoEntry(repo_name="acme-git", alias="git"),
                RepoEntry(repo_name="govc"),
            ],
        )
        assert ws.all_repos() == {"acme-git", "govc"}

    def test_find_repo_categories(self) -> None:
        """Find categories containing a repo."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["cat1"] = Category(
            path="cat1",
            entries=[RepoEntry(repo_name="a"), RepoEntry(repo_name="b")],
        )
        ws.categories["cat2"] = Category(
            path="cat2",
            entries=[RepoEntry(repo_name="b"), RepoEntry(repo_name="c")],
        )
        assert ws.find_repo_categories("b") == ["cat1", "cat2"]
        assert ws.find_repo_categories("a") == ["cat1"]
        assert ws.find_repo_categories("x") == []

    def test_find_repo_categories_with_alias(self) -> None:
        """Find categories by repo name, not by alias."""
        ws = Workspace(path=Path("/workspace"))
        ws.categories["cat1"] = Category(
            path="cat1",
            entries=[RepoEntry(repo_name="acme-git", alias="git")],
        )
        # Should find by repo_name
        assert ws.find_repo_categories("acme-git") == ["cat1"]
        # Should NOT find by alias
        assert ws.find_repo_categories("git") == []


class TestConfig:
    """Tests for Config dataclass."""

    def test_all_repos(self) -> None:
        """Get all repos across all workspaces."""
        config = Config(code_path=Path("/code"))
        ws1 = Workspace(path=Path("/ws1"))
        ws1.categories["cat1"] = Category(
            path="cat1",
            entries=[RepoEntry(repo_name="a"), RepoEntry(repo_name="b")],
        )
        ws2 = Workspace(path=Path("/ws2"))
        ws2.categories["cat2"] = Category(
            path="cat2",
            entries=[RepoEntry(repo_name="b"), RepoEntry(repo_name="c")],
        )
        config.workspaces = {"ws1": ws1, "ws2": ws2}

        assert config.all_repos() == {"a", "b", "c"}

    def test_find_repo_locations(self) -> None:
        """Find all locations of a repo."""
        config = Config(code_path=Path("/code"))
        ws1 = Workspace(path=Path("/ws1"))
        ws1.categories["cat1"] = Category(
            path="cat1", entries=[RepoEntry(repo_name="a")]
        )
        ws2 = Workspace(path=Path("/ws2"))
        ws2.categories["cat2"] = Category(
            path="cat2", entries=[RepoEntry(repo_name="a")]
        )
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
