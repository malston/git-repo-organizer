# ABOUTME: Data models for the git repository organizer.
# ABOUTME: Defines Config, Workspace, and related dataclasses.
"""Data models for gro configuration and workspace management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Category:
    """A category within a workspace containing repo symlinks."""

    path: str  # e.g., "vmware/vsphere" or "." for root
    repos: list[str] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Check if this is the root category (symlinks directly to workspace)."""
        return self.path == "."


@dataclass
class Workspace:
    """A workspace directory containing organized symlinks to repos."""

    path: Path  # Full path, e.g., ~/workspace expanded to /Users/mark/workspace
    categories: dict[str, Category] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Get the workspace name (basename of path)."""
        return self.path.name

    def get_category(self, category_path: str) -> Category | None:
        """Get a category by its path."""
        return self.categories.get(category_path)

    def get_or_create_category(self, category_path: str) -> Category:
        """Get a category, creating it if it doesn't exist."""
        if category_path not in self.categories:
            self.categories[category_path] = Category(path=category_path)
        return self.categories[category_path]

    def all_repos(self) -> set[str]:
        """Get all repo names across all categories."""
        repos: set[str] = set()
        for category in self.categories.values():
            repos.update(category.repos)
        return repos

    def find_repo_categories(self, repo_name: str) -> list[str]:
        """Find all categories containing a repo."""
        return [
            cat_path
            for cat_path, category in self.categories.items()
            if repo_name in category.repos
        ]


@dataclass
class Config:
    """Configuration for the git repository organizer."""

    code_path: Path  # Where actual repos are cloned
    workspaces: dict[str, Workspace] = field(default_factory=dict)

    def get_workspace(self, name: str) -> Workspace | None:
        """Get a workspace by name."""
        return self.workspaces.get(name)

    def get_workspace_by_path(self, path: Path) -> Workspace | None:
        """Get a workspace by its full path."""
        for workspace in self.workspaces.values():
            if workspace.path == path:
                return workspace
        return None

    def all_repos(self) -> set[str]:
        """Get all repo names across all workspaces."""
        repos: set[str] = set()
        for workspace in self.workspaces.values():
            repos.update(workspace.all_repos())
        return repos

    def find_repo_locations(self, repo_name: str) -> list[tuple[str, str]]:
        """Find all locations of a repo as (workspace_name, category_path) tuples."""
        locations: list[tuple[str, str]] = []
        for ws_name, workspace in self.workspaces.items():
            for cat_path in workspace.find_repo_categories(repo_name):
                locations.append((ws_name, cat_path))
        return locations


@dataclass
class RepoStatus:
    """Status of a repository in the system."""

    name: str
    exists_in_code: bool
    locations: list[tuple[str, str]]  # (workspace_name, category_path)
    symlink_status: dict[tuple[str, str], str] = field(default_factory=dict)
    # symlink_status values: "ok", "missing", "wrong_target", "not_symlink"

    @property
    def is_orphaned(self) -> bool:
        """Check if repo exists but has no configured locations."""
        return self.exists_in_code and len(self.locations) == 0

    @property
    def is_missing(self) -> bool:
        """Check if repo is configured but doesn't exist."""
        return not self.exists_in_code and len(self.locations) > 0


@dataclass
class SyncPlan:
    """Plan for syncing config with actual state."""

    repos_to_add: list[str]  # In code but not in config
    repos_missing: list[str]  # In config but not in code
    symlinks_to_create: list[tuple[str, str, str]]  # (workspace, category, repo)
    symlinks_to_update: list[tuple[str, str, str]]  # (workspace, category, repo)
    symlinks_to_remove: list[tuple[str, str, str]]  # (workspace, category, repo)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes to make."""
        return bool(
            self.repos_to_add
            or self.repos_missing
            or self.symlinks_to_create
            or self.symlinks_to_update
            or self.symlinks_to_remove
        )
