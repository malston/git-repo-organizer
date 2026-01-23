# ABOUTME: Unit tests for gro configuration handling.
# ABOUTME: Tests loading, saving, and validating YAML config files.
"""Tests for gro.config."""

from pathlib import Path

import pytest

from gro.config import (
    ConfigError,
    create_default_config,
    expand_path,
    load_config,
    parse_config,
    save_config,
    serialize_config,
    validate_config,
)


class TestExpandPath:
    """Tests for expand_path function."""

    def test_expands_tilde(self) -> None:
        """Tilde is expanded to home directory."""
        result = expand_path("~/foo")
        assert not str(result).startswith("~")
        assert result.is_absolute()

    def test_resolves_path(self) -> None:
        """Path is resolved to absolute."""
        result = expand_path("./foo")
        assert result.is_absolute()


class TestParseConfig:
    """Tests for parse_config function."""

    def test_minimal_config(self) -> None:
        """Parse config with only code path."""
        data = {"code": "~/code"}
        config = parse_config(data)
        assert config.code_path == Path.home() / "code"
        assert config.workspaces == {}

    def test_with_workspaces(self) -> None:
        """Parse config with workspaces."""
        data = {
            "code": "~/code",
            "workspaces": ["~/workspace", "~/projects"],
            "workspace": {
                ".": ["foo"],
                "vmware": ["bar"],
            },
        }
        config = parse_config(data)
        assert len(config.workspaces) == 2
        assert "workspace" in config.workspaces
        assert "projects" in config.workspaces

        ws = config.workspaces["workspace"]
        assert "." in ws.categories
        assert "vmware" in ws.categories
        assert "foo" in ws.categories["."].repos

    def test_missing_code_raises(self) -> None:
        """Missing code field raises ConfigError."""
        with pytest.raises(ConfigError, match="missing required 'code'"):
            parse_config({})

    def test_basename_collision_raises(self) -> None:
        """Duplicate workspace basenames raise ConfigError."""
        data = {
            "code": "~/code",
            "workspaces": ["/path/to/work", "/other/path/to/work"],
        }
        with pytest.raises(ConfigError, match="collision"):
            parse_config(data)

    def test_invalid_workspace_config_raises(self) -> None:
        """Non-dict workspace config raises ConfigError."""
        data = {
            "code": "~/code",
            "workspaces": ["~/workspace"],
            "workspace": "invalid",
        }
        with pytest.raises(ConfigError, match="must be a mapping"):
            parse_config(data)

    def test_invalid_category_raises(self) -> None:
        """Non-list category raises ConfigError."""
        data = {
            "code": "~/code",
            "workspaces": ["~/workspace"],
            "workspace": {"cat": "not-a-list"},
        }
        with pytest.raises(ConfigError, match="must be a list"):
            parse_config(data)


class TestSerializeConfig:
    """Tests for serialize_config function."""

    def test_roundtrip(self) -> None:
        """Config survives serialize/parse roundtrip."""
        original = create_default_config()
        original.workspaces["workspace"].categories["."] = __import__(
            "gro.models", fromlist=["Category"]
        ).Category(path=".", repos=["foo", "bar"])

        data = serialize_config(original)
        restored = parse_config(data)

        assert restored.code_path == original.code_path
        assert len(restored.workspaces) == len(original.workspaces)

    def test_uses_tilde_for_home(self) -> None:
        """Paths under home directory use ~ prefix."""
        config = create_default_config()
        data = serialize_config(config)
        assert data["code"].startswith("~/")


class TestLoadSaveConfig:
    """Tests for load_config and save_config functions."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Config can be saved and loaded."""
        config_path = tmp_path / "config.yaml"
        config = create_default_config(
            code_path=tmp_path / "code",
            workspace_paths=[tmp_path / "workspace"],
        )

        save_config(config, config_path)
        assert config_path.exists()

        loaded = load_config(config_path)
        assert loaded.code_path == config.code_path

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        """Loading nonexistent file raises ConfigError."""
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.yaml")


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    def test_defaults(self) -> None:
        """Default config uses ~/code and ~/workspace."""
        config = create_default_config()
        assert config.code_path == Path.home() / "code"
        assert "workspace" in config.workspaces
        assert config.workspaces["workspace"].path == Path.home() / "workspace"

    def test_custom_paths(self, tmp_path: Path) -> None:
        """Custom paths are used."""
        config = create_default_config(
            code_path=tmp_path / "mycode",
            workspace_paths=[tmp_path / "ws1", tmp_path / "ws2"],
        )
        assert config.code_path == tmp_path / "mycode"
        assert len(config.workspaces) == 2


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_warns_on_missing_code_dir(self, tmp_path: Path) -> None:
        """Warns if code directory doesn't exist."""
        config = create_default_config(
            code_path=tmp_path / "nonexistent",
            workspace_paths=[tmp_path / "ws"],
        )
        warnings = validate_config(config)
        assert any("Code directory does not exist" in w for w in warnings)

    def test_warns_on_missing_workspace_dir(self, tmp_path: Path) -> None:
        """Warns if workspace directory doesn't exist."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        config = create_default_config(
            code_path=code_path,
            workspace_paths=[tmp_path / "nonexistent"],
        )
        warnings = validate_config(config)
        assert any("Workspace directory does not exist" in w for w in warnings)
