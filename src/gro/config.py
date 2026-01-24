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


def parse_config(data: dict[str, Any]) -> Config:
    """
    Parse config data into Config object.

    Args:
        data: Raw config data from YAML.

    Returns:
        Parsed Config object.

    Raises:
        ConfigError: If config structure is invalid.
    """
    # Validate required fields
    if "code" not in data:
        raise ConfigError("Config missing required 'code' field")

    code_path = expand_path(data["code"])

    # Parse workspaces list
    workspace_paths: list[Path] = []
    if "workspaces" in data:
        if not isinstance(data["workspaces"], list):
            raise ConfigError("'workspaces' must be a list")
        workspace_paths = [expand_path(p) for p in data["workspaces"]]

    # Check for basename collisions
    basenames: dict[str, Path] = {}
    for ws_path in workspace_paths:
        name = ws_path.name
        if name in basenames:
            raise ConfigError(
                f"Workspace basename collision: '{name}' used by both "
                f"{basenames[name]} and {ws_path}"
            )
        basenames[name] = ws_path

    # Parse workspace configurations
    workspaces: dict[str, Workspace] = {}

    for ws_path in workspace_paths:
        ws_name = ws_path.name
        workspace = Workspace(path=ws_path)

        # Look for workspace config section
        if ws_name in data:
            ws_data = data[ws_name]
            if not isinstance(ws_data, dict):
                raise ConfigError(f"Workspace '{ws_name}' config must be a mapping")

            for cat_path, repo_strs in ws_data.items():
                if repo_strs is None:
                    repo_strs = []
                if not isinstance(repo_strs, list):
                    raise ConfigError(
                        f"Category '{cat_path}' in workspace '{ws_name}' must be a list"
                    )
                # Parse repo strings into RepoEntry objects
                entries: list[RepoEntry] = []
                for repo_str in repo_strs:
                    if not isinstance(repo_str, str):
                        raise ConfigError(
                            f"Repo names must be strings, got {type(repo_str).__name__} in "
                            f"'{ws_name}/{cat_path}'"
                        )
                    entries.append(RepoEntry.from_string(repo_str))
                workspace.categories[cat_path] = Category(path=cat_path, entries=entries)

        workspaces[ws_name] = workspace

    return Config(code_path=code_path, workspaces=workspaces)


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


def serialize_config(config: Config) -> dict[str, Any]:
    """
    Serialize Config object to dict for YAML.

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

    # Workspaces list
    if config.workspaces:
        data["workspaces"] = [path_str(ws.path) for ws in config.workspaces.values()]

    # Workspace configurations
    for ws_name, workspace in config.workspaces.items():
        if workspace.categories:
            ws_data: dict[str, list[str]] = {}
            for cat_path, category in sorted(workspace.categories.items()):
                ws_data[cat_path] = sorted(
                    [entry.to_string() for entry in category.entries]
                )
            if ws_data:
                data[ws_name] = ws_data

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
