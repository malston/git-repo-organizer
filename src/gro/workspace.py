# ABOUTME: Workspace scanning and symlink management for gro.
# ABOUTME: Handles discovering repos and creating/managing symlinks.
"""Workspace operations for gro."""

from __future__ import annotations

import os
from pathlib import Path

from gro.models import Config, RepoStatus, SyncPlan


def scan_code_dir(code_path: Path) -> list[str]:
    """
    Scan the code directory for git repositories.

    Args:
        code_path: Path to the code directory.

    Returns:
        List of repository names (directory names containing .git).
    """
    if not code_path.exists():
        return []

    repos: list[str] = []
    for item in code_path.iterdir():
        if item.is_dir() and (item / ".git").exists():
            repos.append(item.name)

    return sorted(repos)


def scan_workspace_symlinks(workspace_path: Path) -> dict[str, list[str]]:
    """
    Scan a workspace directory for symlinks.

    Args:
        workspace_path: Path to the workspace directory.

    Returns:
        Dict mapping category paths to lists of repo names.
        Category "." means symlinks at workspace root.
    """
    if not workspace_path.exists():
        return {}

    result: dict[str, list[str]] = {}

    def scan_dir(dir_path: Path, category_prefix: str) -> None:
        """Recursively scan directory for symlinks."""
        if not dir_path.exists():
            return

        for item in dir_path.iterdir():
            if item.is_symlink():
                # This is a symlink to a repo
                cat_path = category_prefix if category_prefix else "."
                if cat_path not in result:
                    result[cat_path] = []
                result[cat_path].append(item.name)
            elif item.is_dir():
                # Recurse into subdirectory
                new_prefix = f"{category_prefix}/{item.name}" if category_prefix else item.name
                scan_dir(item, new_prefix)

    scan_dir(workspace_path, "")
    return result


def scan_workspace_non_symlinks(workspace_path: Path) -> dict[str, list[str]]:
    """
    Scan a workspace directory for non-symlink directories (potential direct clones).

    Args:
        workspace_path: Path to the workspace directory.

    Returns:
        Dict mapping category paths to lists of directory names that are not symlinks.
        Category "." means directories at workspace root.
    """
    if not workspace_path.exists():
        return {}

    result: dict[str, list[str]] = {}

    def scan_dir(dir_path: Path, category_prefix: str) -> None:
        """Recursively scan directory for non-symlink directories."""
        if not dir_path.exists():
            return

        for item in dir_path.iterdir():
            if item.is_symlink():
                # Skip symlinks - they're managed by gro
                continue
            elif item.is_dir():
                # Check if this looks like a repo (has .git)
                if (item / ".git").exists():
                    # This is a non-symlink repo directory
                    cat_path = category_prefix if category_prefix else "."
                    if cat_path not in result:
                        result[cat_path] = []
                    result[cat_path].append(item.name)
                else:
                    # Recurse into subdirectory (category folder)
                    new_prefix = f"{category_prefix}/{item.name}" if category_prefix else item.name
                    scan_dir(item, new_prefix)

    scan_dir(workspace_path, "")
    return result


def get_symlink_path(workspace_path: Path, category_path: str, repo_name: str) -> Path:
    """
    Get the full path for a symlink.

    Args:
        workspace_path: Path to the workspace.
        category_path: Category path (e.g., "vmware/vsphere" or ".").
        repo_name: Name of the repo.

    Returns:
        Full path where symlink should be.
    """
    if category_path == ".":
        return workspace_path / repo_name
    return workspace_path / category_path / repo_name


def get_symlink_target(code_path: Path, repo_name: str) -> Path:
    """
    Get the target path for a symlink.

    Args:
        code_path: Path to the code directory.
        repo_name: Name of the repo.

    Returns:
        Full path to the actual repo.
    """
    return code_path / repo_name


def create_symlink(source: Path, target: Path, dry_run: bool = False) -> bool:
    """
    Create a symlink from source to target.

    Args:
        source: Path where symlink will be created.
        target: Path the symlink will point to.
        dry_run: If True, don't actually create the symlink.

    Returns:
        True if symlink was created (or would be in dry_run).
    """
    if dry_run:
        return True

    # Create parent directories
    source.parent.mkdir(parents=True, exist_ok=True)

    # Create relative symlink for cleaner paths
    try:
        rel_target = os.path.relpath(target, source.parent)
        source.symlink_to(rel_target)
        return True
    except OSError:
        return False


def remove_symlink(path: Path, dry_run: bool = False) -> bool:
    """
    Remove a symlink.

    Args:
        path: Path to the symlink.
        dry_run: If True, don't actually remove.

    Returns:
        True if symlink was removed (or would be in dry_run).
    """
    if not path.is_symlink():
        return False

    if dry_run:
        return True

    try:
        path.unlink()
        return True
    except OSError:
        return False


def update_symlink(source: Path, target: Path, dry_run: bool = False) -> bool:
    """
    Update a symlink to point to a new target.

    Args:
        source: Path to the symlink.
        target: New target path.
        dry_run: If True, don't actually update.

    Returns:
        True if symlink was updated (or would be in dry_run).
    """
    if dry_run:
        return True

    if source.is_symlink():
        source.unlink()

    return create_symlink(source, target, dry_run=False)


def check_symlink_status(source: Path, expected_target: Path) -> str:
    """
    Check the status of a symlink.

    Args:
        source: Path where symlink should be.
        expected_target: Path it should point to.

    Returns:
        Status string: "ok", "missing", "wrong_target", "not_symlink"
    """
    if not source.exists() and not source.is_symlink():
        return "missing"

    if not source.is_symlink():
        return "not_symlink"

    # Resolve the symlink and compare
    try:
        actual_target = source.resolve()
        if actual_target == expected_target.resolve():
            return "ok"
        return "wrong_target"
    except OSError:
        return "wrong_target"


def get_repo_status(config: Config, repo_name: str) -> RepoStatus:
    """
    Get the full status of a repository.

    Args:
        config: The configuration.
        repo_name: Name of the repo.

    Returns:
        RepoStatus with all information about the repo.
    """
    repo_path = config.code_path / repo_name
    exists = repo_path.exists() and (repo_path / ".git").exists()

    locations = config.find_repo_locations(repo_name)

    symlink_status: dict[tuple[str, str], str] = {}
    for ws_name, cat_path in locations:
        workspace = config.workspaces[ws_name]
        symlink_path = get_symlink_path(workspace.path, cat_path, repo_name)
        target_path = get_symlink_target(config.code_path, repo_name)
        symlink_status[(ws_name, cat_path)] = check_symlink_status(symlink_path, target_path)

    return RepoStatus(
        name=repo_name,
        exists_in_code=exists,
        locations=locations,
        symlink_status=symlink_status,
    )


def create_sync_plan(config: Config) -> SyncPlan:
    """
    Create a plan for syncing config with actual state.

    Args:
        config: The configuration.

    Returns:
        SyncPlan describing all changes needed.
    """
    # Get all repos in code directory
    code_repos = set(scan_code_dir(config.code_path))

    # Get all repos mentioned in config
    config_repos = config.all_repos()

    # Repos to add to config (in code but not configured)
    repos_to_add = sorted(code_repos - config_repos)

    # Repos missing from code (configured but not present)
    repos_missing = sorted(config_repos - code_repos)

    # Check symlink status for all configured repos
    symlinks_to_create: list[tuple[str, str, str]] = []
    symlinks_to_update: list[tuple[str, str, str]] = []
    symlinks_to_remove: list[tuple[str, str, str]] = []

    for ws_name, workspace in config.workspaces.items():
        for cat_path, category in workspace.categories.items():
            for repo_name in category.repos:
                symlink_path = get_symlink_path(workspace.path, cat_path, repo_name)
                target_path = get_symlink_target(config.code_path, repo_name)

                status = check_symlink_status(symlink_path, target_path)

                if status == "missing":
                    # Only create if repo exists
                    if repo_name in code_repos:
                        symlinks_to_create.append((ws_name, cat_path, repo_name))
                elif status == "wrong_target":
                    if repo_name in code_repos:
                        symlinks_to_update.append((ws_name, cat_path, repo_name))
                elif status == "not_symlink":
                    # Can't update - there's a real file/dir there
                    pass  # Will be reported as error

        # Check for orphaned symlinks (exist but not in config)
        existing_symlinks = scan_workspace_symlinks(workspace.path)
        for cat_path, repos in existing_symlinks.items():
            maybe_category = workspace.categories.get(cat_path)
            configured_repos = set(maybe_category.repos) if maybe_category else set()
            for repo_name in repos:
                if repo_name not in configured_repos:
                    symlinks_to_remove.append((ws_name, cat_path, repo_name))

    # Check for non-symlink directories in workspaces
    non_symlink_dirs: list[tuple[str, str, str]] = []
    for ws_name, workspace in config.workspaces.items():
        non_symlinks = scan_workspace_non_symlinks(workspace.path)
        for cat_path, dir_names in non_symlinks.items():
            for dir_name in dir_names:
                non_symlink_dirs.append((ws_name, cat_path, dir_name))

    return SyncPlan(
        repos_to_add=repos_to_add,
        repos_missing=repos_missing,
        symlinks_to_create=symlinks_to_create,
        symlinks_to_update=symlinks_to_update,
        symlinks_to_remove=symlinks_to_remove,
        non_symlink_dirs=non_symlink_dirs,
    )


def apply_sync_plan(
    config: Config,
    plan: SyncPlan,
    dry_run: bool = False,
    remove_orphans: bool = False,
) -> dict[str, list[str]]:
    """
    Apply a sync plan.

    Args:
        config: The configuration.
        plan: The sync plan to apply.
        dry_run: If True, don't make changes.
        remove_orphans: If True, remove orphaned symlinks.

    Returns:
        Dict with "created", "updated", "removed", "errors" lists.
    """
    results: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "removed": [],
        "errors": [],
    }

    # Create symlinks
    for ws_name, cat_path, repo_name in plan.symlinks_to_create:
        workspace = config.workspaces[ws_name]
        symlink_path = get_symlink_path(workspace.path, cat_path, repo_name)
        target_path = get_symlink_target(config.code_path, repo_name)

        if create_symlink(symlink_path, target_path, dry_run=dry_run):
            results["created"].append(f"{ws_name}/{cat_path}/{repo_name}")
        else:
            results["errors"].append(f"Failed to create: {symlink_path}")

    # Update symlinks
    for ws_name, cat_path, repo_name in plan.symlinks_to_update:
        workspace = config.workspaces[ws_name]
        symlink_path = get_symlink_path(workspace.path, cat_path, repo_name)
        target_path = get_symlink_target(config.code_path, repo_name)

        if update_symlink(symlink_path, target_path, dry_run=dry_run):
            results["updated"].append(f"{ws_name}/{cat_path}/{repo_name}")
        else:
            results["errors"].append(f"Failed to update: {symlink_path}")

    # Remove orphaned symlinks
    if remove_orphans:
        for ws_name, cat_path, repo_name in plan.symlinks_to_remove:
            workspace = config.workspaces[ws_name]
            symlink_path = get_symlink_path(workspace.path, cat_path, repo_name)

            if remove_symlink(symlink_path, dry_run=dry_run):
                results["removed"].append(f"{ws_name}/{cat_path}/{repo_name}")
            else:
                results["errors"].append(f"Failed to remove: {symlink_path}")

    return results


def cleanup_empty_directories(workspace_path: Path, dry_run: bool = False) -> list[Path]:
    """
    Remove empty directories in a workspace.

    Args:
        workspace_path: Path to the workspace.
        dry_run: If True, don't actually remove.

    Returns:
        List of directories removed (or would be removed).
    """
    removed: list[Path] = []

    def cleanup_dir(dir_path: Path) -> bool:
        """Recursively clean up directory, return True if empty."""
        if not dir_path.exists():
            return True

        # First, clean up subdirectories
        has_content = False
        for item in list(dir_path.iterdir()):
            if item.is_dir() and not item.is_symlink():
                if not cleanup_dir(item):
                    has_content = True
            else:
                has_content = True

        # If directory is now empty, remove it
        if not has_content and dir_path != workspace_path:
            if not dry_run:
                dir_path.rmdir()
            removed.append(dir_path)
            return True

        return False

    cleanup_dir(workspace_path)
    return removed
