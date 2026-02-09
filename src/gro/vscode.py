# ABOUTME: VS Code workspace file generation from gro configuration.
# ABOUTME: Generates .code-workspace files with relative paths to workspace symlinks.
"""VS Code workspace file generation for gro."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from gro.models import Config


def workspace_file_name(ws_name: str, category_path: str | None = None) -> str:
    """Generate a .code-workspace filename.

    Args:
        ws_name: Workspace name.
        category_path: Optional category path to filter by.

    Returns:
        Filename like "workspace.code-workspace" or "workspace-tools.code-workspace".
    """
    if category_path is None:
        return f"{ws_name}.code-workspace"
    if category_path == ".":
        return f"{ws_name}-root.code-workspace"
    # Use category name as filename, replacing slashes with dashes
    cat_slug = category_path.replace("/", "-")
    return f"{cat_slug}.code-workspace"


def generate_workspace_data(
    config: Config,
    ws_name: str,
    category_path: str | None = None,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """Build VS Code workspace data structure.

    Args:
        config: The gro configuration.
        ws_name: Workspace name to generate for.
        category_path: Optional category path to filter repos.
        output_dir: Directory where the workspace file will be written,
            used to compute relative paths.

    Returns:
        Dict with "folders" and "settings" keys.

    Raises:
        ValueError: If workspace or category not found.
    """
    workspace = config.get_workspace(ws_name)
    if workspace is None:
        available = ", ".join(sorted(config.workspaces.keys()))
        raise ValueError(
            f"Workspace '{ws_name}' not found. Available: {available}"
        )

    if category_path is not None:
        category = workspace.get_category(category_path)
        if category is None:
            available = ", ".join(sorted(workspace.categories.keys()))
            raise ValueError(
                f"Category '{category_path}' not found in workspace '{ws_name}'. "
                f"Available: {available}"
            )
        categories = {category_path: category}
    else:
        categories = workspace.categories

    # Compute relative path from output_dir to workspace path
    try:
        rel_to_ws = PurePosixPath(output_dir.resolve().relative_to(
            workspace.path.resolve()
        ))
        # This means output_dir is inside workspace -- unlikely but handle it
        prefix = PurePosixPath("/".join([".."] * len(rel_to_ws.parts))) / workspace.path.name
    except ValueError:
        # output_dir is not inside workspace path -- compute relative path
        rel = PurePosixPath(Path(*_relative_parts(output_dir.resolve(), workspace.path.resolve())))
        prefix = rel

    # Collect folders, deduplicating by symlink_name
    seen: set[str] = set()
    folders: list[dict[str, str]] = []

    for cat_path, category in categories.items():
        for entry in category.entries:
            name = entry.symlink_name
            if name in seen:
                continue
            seen.add(name)

            # Build the path: relative prefix + category subpath + symlink name
            folder_path = str(prefix / name) if cat_path == "." else str(prefix / cat_path / name)

            folders.append({"name": name, "path": folder_path})

    folders.sort(key=lambda f: f["name"])

    return {"folders": folders, "settings": {}}


def _relative_parts(from_path: Path, to_path: Path) -> list[str]:
    """Compute relative path parts from from_path to to_path.

    Returns a list of path components that navigate from from_path to to_path.
    """
    # Find common ancestor
    from_parts = from_path.parts
    to_parts = to_path.parts

    common_length = 0
    for a, b in zip(from_parts, to_parts, strict=False):
        if a != b:
            break
        common_length += 1

    # Go up from from_path to common ancestor
    ups = len(from_parts) - common_length
    # Then down to to_path
    downs = list(to_parts[common_length:])

    parts: list[str] = [".."] * ups + downs
    return parts


def write_workspace_file(data: dict[str, Any], output_path: Path) -> None:
    """Write workspace data as JSON to a file.

    Args:
        data: Workspace data dict to write.
        output_path: Path to write the .code-workspace file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2)
    output_path.write_text(content + "\n")
