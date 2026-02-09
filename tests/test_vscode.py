# ABOUTME: Unit tests for VS Code workspace file generation.
# ABOUTME: Tests workspace_file_name, generate_workspace_data, and write_workspace_file.
"""Tests for gro.vscode."""

import json
from pathlib import Path

import pytest

from gro.models import Category, Config, RepoEntry, Workspace
from gro.vscode import generate_workspace_data, workspace_file_name, write_workspace_file


class TestWorkspaceFileName:
    """Tests for workspace_file_name function."""

    def test_workspace_only(self) -> None:
        """Generates filename from workspace name alone."""
        assert workspace_file_name("workspace") == "workspace.code-workspace"

    def test_root_category(self) -> None:
        """Root category '.' uses workspace name with root suffix."""
        assert workspace_file_name("workspace", ".") == "workspace-root.code-workspace"

    def test_simple_category(self) -> None:
        """Category name used as filename."""
        assert workspace_file_name("workspace", "tools") == "tools.code-workspace"

    def test_nested_category(self) -> None:
        """Nested category slashes become dashes."""
        assert (
            workspace_file_name("workspace", "vmware/vsphere")
            == "vmware-vsphere.code-workspace"
        )

    def test_deeply_nested_category(self) -> None:
        """Multiple slashes all become dashes."""
        assert (
            workspace_file_name("workspace", "a/b/c")
            == "a-b-c.code-workspace"
        )


class TestGenerateWorkspaceData:
    """Tests for generate_workspace_data function."""

    def _make_config(self, tmp_path: Path) -> Config:
        """Create a test config with repos across categories."""
        code_path = tmp_path / "code"
        ws = Workspace(path=tmp_path / "workspace")
        ws.categories["."] = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="alpha-repo"),
                RepoEntry(repo_name="zebra-repo"),
            ],
        )
        ws.categories["vmware/vsphere"] = Category(
            path="vmware/vsphere",
            entries=[
                RepoEntry(repo_name="pyvmomi"),
                RepoEntry(repo_name="govc"),
            ],
        )
        ws.categories["tools"] = Category(
            path="tools",
            entries=[RepoEntry(repo_name="my-tool")],
        )
        config = Config(code_path=code_path, workspaces={"workspace": ws})
        return config

    def test_all_repos_in_workspace(self, tmp_path: Path) -> None:
        """All repos from all categories appear in folders."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)

        folder_names = {f["name"] for f in data["folders"]}
        assert folder_names == {"alpha-repo", "zebra-repo", "pyvmomi", "govc", "my-tool"}

    def test_folders_use_relative_paths(self, tmp_path: Path) -> None:
        """Folder paths are relative from output_dir to workspace symlink location."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)

        # Root category repos: path is relative to workspace root
        root_folders = {f["name"]: f["path"] for f in data["folders"]}
        assert root_folders["alpha-repo"] == "../workspace/alpha-repo"
        assert root_folders["zebra-repo"] == "../workspace/zebra-repo"

        # Nested category repos: path includes category path
        assert root_folders["pyvmomi"] == "../workspace/vmware/vsphere/pyvmomi"
        assert root_folders["my-tool"] == "../workspace/tools/my-tool"

    def test_folders_sorted_alphabetically(self, tmp_path: Path) -> None:
        """Folders are sorted by name."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)

        names = [f["name"] for f in data["folders"]]
        assert names == sorted(names)

    def test_category_filter(self, tmp_path: Path) -> None:
        """Only repos from specified category appear when filtered."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(
            config, "workspace", category_path="vmware/vsphere", output_dir=output_dir
        )

        folder_names = {f["name"] for f in data["folders"]}
        assert folder_names == {"pyvmomi", "govc"}

    def test_root_category_filter(self, tmp_path: Path) -> None:
        """Root category '.' can be used as filter."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(
            config, "workspace", category_path=".", output_dir=output_dir
        )

        folder_names = {f["name"] for f in data["folders"]}
        assert folder_names == {"alpha-repo", "zebra-repo"}

    def test_deduplication(self, tmp_path: Path) -> None:
        """Same repo in multiple categories appears once."""
        code_path = tmp_path / "code"
        ws = Workspace(path=tmp_path / "workspace")
        ws.categories["."] = Category(
            path=".", entries=[RepoEntry(repo_name="shared-repo")]
        )
        ws.categories["tools"] = Category(
            path="tools", entries=[RepoEntry(repo_name="shared-repo")]
        )
        config = Config(code_path=code_path, workspaces={"workspace": ws})

        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)
        names = [f["name"] for f in data["folders"]]
        assert names.count("shared-repo") == 1

    def test_has_empty_settings(self, tmp_path: Path) -> None:
        """Output includes empty settings dict."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)
        assert data["settings"] == {}

    def test_unknown_workspace_raises(self, tmp_path: Path) -> None:
        """Raises ValueError for unknown workspace name."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        with pytest.raises(ValueError, match="workspace"):
            generate_workspace_data(config, "nonexistent", output_dir=output_dir)

    def test_unknown_workspace_shows_available(self, tmp_path: Path) -> None:
        """Error message lists available workspace names."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        with pytest.raises(ValueError, match="workspace"):
            generate_workspace_data(config, "nonexistent", output_dir=output_dir)

    def test_unknown_category_raises(self, tmp_path: Path) -> None:
        """Raises ValueError for unknown category path."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        with pytest.raises(ValueError, match="nonexistent"):
            generate_workspace_data(
                config, "workspace", category_path="nonexistent", output_dir=output_dir
            )

    def test_unknown_category_shows_available(self, tmp_path: Path) -> None:
        """Error message lists available category paths."""
        config = self._make_config(tmp_path)
        output_dir = tmp_path / "vscode-workspaces"
        with pytest.raises(ValueError, match="vmware/vsphere"):
            generate_workspace_data(
                config, "workspace", category_path="nonexistent", output_dir=output_dir
            )

    def test_aliased_repo_uses_symlink_name(self, tmp_path: Path) -> None:
        """Aliased repos use the alias (symlink_name) as the folder name."""
        code_path = tmp_path / "code"
        ws = Workspace(path=tmp_path / "workspace")
        ws.categories["."] = Category(
            path=".",
            entries=[RepoEntry(repo_name="acme-code", alias="git")],
        )
        config = Config(code_path=code_path, workspaces={"workspace": ws})

        output_dir = tmp_path / "vscode-workspaces"
        data = generate_workspace_data(config, "workspace", output_dir=output_dir)
        assert len(data["folders"]) == 1
        assert data["folders"][0]["name"] == "git"
        assert data["folders"][0]["path"] == "../workspace/git"


class TestWriteWorkspaceFile:
    """Tests for write_workspace_file function."""

    def test_writes_json_file(self, tmp_path: Path) -> None:
        """Writes valid JSON to the specified path."""
        output_path = tmp_path / "test.code-workspace"
        data = {"folders": [{"path": "../workspace/repo", "name": "repo"}], "settings": {}}

        write_workspace_file(data, output_path)

        assert output_path.exists()
        content = json.loads(output_path.read_text())
        assert content == data

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Creates parent directories if they don't exist."""
        output_path = tmp_path / "nested" / "dir" / "test.code-workspace"
        data = {"folders": [], "settings": {}}

        write_workspace_file(data, output_path)

        assert output_path.exists()

    def test_json_is_formatted(self, tmp_path: Path) -> None:
        """Output JSON is human-readable (indented)."""
        output_path = tmp_path / "test.code-workspace"
        data = {"folders": [{"path": "../workspace/repo", "name": "repo"}], "settings": {}}

        write_workspace_file(data, output_path)

        content = output_path.read_text()
        # Indented JSON has newlines
        assert "\n" in content
        # Should be parseable
        assert json.loads(content) == data

    def test_trailing_newline(self, tmp_path: Path) -> None:
        """Output file ends with a newline."""
        output_path = tmp_path / "test.code-workspace"
        data = {"folders": [], "settings": {}}

        write_workspace_file(data, output_path)

        content = output_path.read_text()
        assert content.endswith("\n")
