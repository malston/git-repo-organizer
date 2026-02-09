# ABOUTME: Configuration loading, saving, and validation for gro.
# ABOUTME: Handles YAML parsing and path expansion.
"""Configuration management for gro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from gro.models import Category, Config, RepoEntry, Workspace


class ConfigError(Exception):
    """Error in configuration file."""

    pass


def get_default_config_path() -> Path:
    """Get the default config file path."""
    return Path.home() / ".config" / "gro" / "config.yaml"


def expand_path(path: str | Path) -> Path:
    """Expand ~ and resolve path."""
    return Path(path).expanduser().resolve()


def load_config(path: Path | None = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        path: Path to config file. Uses default if None.

    Returns:
        Loaded Config object.

    Raises:
        ConfigError: If config is invalid or file doesn't exist.
    """
    if path is None:
        path = get_default_config_path()

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e

    if data is None:
        raise ConfigError("Config file is empty")

    return parse_config(data)


def _key_to_workspace_path(key: str) -> Path:
    """Convert a config key to a workspace path.

    Simple names like 'Projects' become ~/Projects.
    Paths starting with ~ or / are used as-is.
    """
    if key.startswith("~") or key.startswith("/"):
        return expand_path(key)
    return expand_path(f"~/{key}")


def parse_config(data: dict[str, Any]) -> Config:
    """
    Parse config data into Config object.

    Config format: Any top-level key except 'code' is a workspace.
    - Simple names like 'Projects' become ~/Projects
    - Paths like '~/work/projects' or '/tmp/ws' are used as-is

    Args:
        data: Raw config data from YAML.

    Returns:
        Parsed Config object.

    Raises:
        ConfigError: If config structure is invalid.
    """
    # Reject old format
    if "workspaces" in data:
        raise ConfigError(
            "The 'workspaces' list is no longer supported. "
            "Use top-level keys for workspaces instead. Example:\n"
            "  code: ~/code\n"
            "  Projects:\n"
            "    .: [repo1, repo2]"
        )

    # Code path defaults to ~/code
    code_path = expand_path(data.get("code", "~/code"))

    # Reserved keys that are not workspace definitions
    reserved_keys = {"code", "vscode_workspaces"}

    # Parse vscode_workspaces path if present
    vscode_ws = data.get("vscode_workspaces")
    vscode_workspaces_path = expand_path(vscode_ws) if vscode_ws else None

    # Collect workspace keys (everything except reserved keys)
    workspace_keys = [k for k in data if k not in reserved_keys]

    # Build workspace paths and check for basename collisions
    basenames: dict[str, tuple[str, Path]] = {}  # basename -> (key, path)
    workspace_paths: dict[str, Path] = {}  # key -> path

    for key in workspace_keys:
        ws_path = _key_to_workspace_path(key)
        ws_name = ws_path.name

        if ws_name in basenames:
            existing_key, existing_path = basenames[ws_name]
            raise ConfigError(
                f"Workspace basename collision: '{ws_name}' used by both "
                f"'{existing_key}' ({existing_path}) and '{key}' ({ws_path})"
            )
        basenames[ws_name] = (key, ws_path)
        workspace_paths[key] = ws_path

    # Parse workspace configurations
    workspaces: dict[str, Workspace] = {}

    for key in workspace_keys:
        ws_path = workspace_paths[key]
        ws_name = ws_path.name
        workspace = Workspace(path=ws_path)

        ws_data = data[key]
        if not isinstance(ws_data, dict):
            raise ConfigError(f"Workspace '{key}' config must be a mapping")

        for cat_path, repo_strs in ws_data.items():
            if repo_strs is None:
                repo_strs = []
            if not isinstance(repo_strs, list):
                raise ConfigError(
                    f"Category '{cat_path}' in workspace '{key}' must be a list"
                )
            # Parse repo strings into RepoEntry objects
            entries: list[RepoEntry] = []
            for repo_str in repo_strs:
                if not isinstance(repo_str, str):
                    raise ConfigError(
                        f"Repo names must be strings, got {type(repo_str).__name__} in "
                        f"'{key}/{cat_path}'"
                    )
                entries.append(RepoEntry.from_string(repo_str))
            workspace.categories[cat_path] = Category(path=cat_path, entries=entries)

        workspaces[ws_name] = workspace

    return Config(
        code_path=code_path,
        workspaces=workspaces,
        vscode_workspaces_path=vscode_workspaces_path,
    )


def save_config(config: Config, path: Path | None = None) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Config object to save.
        path: Path to save to. Uses default if None.
    """
    if path is None:
        path = get_default_config_path()

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    data = serialize_config(config)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _workspace_key(ws_path: Path) -> str:
    """Get the config key for a workspace path.

    Uses simple name if path is directly under home (~/Name -> Name).
    Otherwise uses full path with ~ prefix.
    """
    home = Path.home()
    try:
        rel = ws_path.relative_to(home)
        parts = rel.parts
        if len(parts) == 1:
            # Directly under home: ~/Projects -> Projects
            return parts[0]
        else:
            # Nested: ~/work/projects -> ~/work/projects
            return f"~/{rel}"
    except ValueError:
        # Not under home, use absolute path
        return str(ws_path)


def serialize_config(config: Config) -> dict[str, Any]:
    """
    Serialize Config object to dict for YAML.

    Output format uses top-level keys for workspaces (no 'workspaces' list).
    Simple paths like ~/Projects are serialized as just 'Projects'.

    Args:
        config: Config object to serialize.

    Returns:
        Dict suitable for YAML dump.
    """
    data: dict[str, Any] = {}

    # Use ~ for home directory paths for readability
    home = Path.home()

    def path_str(p: Path) -> str:
        try:
            rel = p.relative_to(home)
            return f"~/{rel}"
        except ValueError:
            return str(p)

    data["code"] = path_str(config.code_path)

    if config.vscode_workspaces_path is not None:
        data["vscode_workspaces"] = path_str(config.vscode_workspaces_path)

    # Workspace configurations as top-level keys
    for workspace in config.workspaces.values():
        ws_key = _workspace_key(workspace.path)
        ws_data: dict[str, list[str]] = {}
        for cat_path, category in sorted(workspace.categories.items()):
            ws_data[cat_path] = sorted(
                [entry.to_string() for entry in category.entries]
            )
        # Always include the workspace, even if no categories yet
        data[ws_key] = ws_data if ws_data else {}

    return data


def create_default_config(
    code_path: Path | None = None,
    workspace_paths: list[Path] | None = None,
) -> Config:
    """
    Create a default configuration.

    Args:
        code_path: Path for code directory. Defaults to ~/code.
        workspace_paths: List of workspace paths. Defaults to [~/workspace].

    Returns:
        New Config object.
    """
    resolved_code_path = Path.home() / "code" if code_path is None else expand_path(code_path)

    if workspace_paths is None:
        workspace_paths = [Path.home() / "workspace"]
    else:
        workspace_paths = [expand_path(p) for p in workspace_paths]

    workspaces: dict[str, Workspace] = {}
    for ws_path in workspace_paths:
        workspaces[ws_path.name] = Workspace(path=ws_path)

    return Config(code_path=resolved_code_path, workspaces=workspaces)


def validate_config(config: Config) -> list[str]:
    """
    Validate a config and return list of warnings.

    Args:
        config: Config to validate.

    Returns:
        List of warning messages (empty if valid).
    """
    warnings: list[str] = []

    # Check code path exists
    if not config.code_path.exists():
        warnings.append(f"Code directory does not exist: {config.code_path}")

    # Check workspace paths exist
    for workspace in config.workspaces.values():
        if not workspace.path.exists():
            warnings.append(f"Workspace directory does not exist: {workspace.path}")

    # Check for duplicate repo assignments within same workspace
    for ws_name, workspace in config.workspaces.items():
        repo_locations: dict[str, list[str]] = {}
        for cat_path, category in workspace.categories.items():
            for entry in category.entries:
                if entry.repo_name not in repo_locations:
                    repo_locations[entry.repo_name] = []
                repo_locations[entry.repo_name].append(cat_path)

        # Note: Having a repo in multiple categories is allowed, just informational
        for repo, locations in repo_locations.items():
            if len(locations) > 1:
                warnings.append(
                    f"Repo '{repo}' appears in multiple categories in '{ws_name}': "
                    f"{', '.join(locations)}"
                )

    # Check for duplicate symlink names within same category
    for ws_name, workspace in config.workspaces.items():
        for cat_path, category in workspace.categories.items():
            symlink_names: dict[str, list[str]] = {}
            for entry in category.entries:
                if entry.symlink_name not in symlink_names:
                    symlink_names[entry.symlink_name] = []
                symlink_names[entry.symlink_name].append(entry.repo_name)

            for symlink_name, repos in symlink_names.items():
                if len(repos) > 1:
                    warnings.append(
                        f"Duplicate symlink name '{symlink_name}' in '{ws_name}/{cat_path}': "
                        f"repos {', '.join(repos)}"
                    )

    # Check for category paths that conflict with repo names in parent categories
    for ws_name, workspace in config.workspaces.items():
        # Build map of category path -> symlink names in that category
        category_symlinks: dict[str, set[str]] = {}
        for cat_path, category in workspace.categories.items():
            category_symlinks[cat_path] = category.symlink_names

        # For each category, check if its path conflicts with a symlink name in a parent
        for cat_path in workspace.categories:
            if cat_path == ".":
                continue  # Root category can't conflict

            # Split the path into parts
            parts = cat_path.split("/")

            # Check each prefix of the path
            for i in range(len(parts)):
                # The prefix path (parent category)
                parent_path = "." if i == 0 else "/".join(parts[:i])

                # The component that would need to be a directory
                component = parts[i]

                # Check if parent category has a symlink with this name
                if parent_path in category_symlinks and component in category_symlinks[parent_path]:
                    warnings.append(
                        f"Category path '{cat_path}' in workspace '{ws_name}' "
                        f"conflicts with repo '{component}' in category '{parent_path}'"
                    )
                    break  # Only report first conflict in path

    return warnings
