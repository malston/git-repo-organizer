# ABOUTME: Integration tests for gro CLI commands.
# ABOUTME: Tests init, status, apply, sync, and add commands.
"""Tests for gro.cli."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from gro.cli import main
from gro.config import load_config, save_config
from gro.models import Category, Config, Workspace


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def test_env(tmp_path: Path) -> dict[str, Path]:
    """Create test environment with code and workspace directories."""
    code_path = tmp_path / "code"
    code_path.mkdir()

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    config_path = tmp_path / "config.yaml"

    return {
        "code": code_path,
        "workspace": workspace_path,
        "config": config_path,
    }


class TestMain:
    """Tests for main CLI group."""

    def test_help(self, runner: CliRunner) -> None:
        """Shows help message."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "GRO - Git Repository Organizer" in result.output

    def test_dry_run_flag(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Dry run flag is passed to context."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--dry-run",
                "init",
                "--code",
                str(test_env["code"]),
                "--workspace",
                str(test_env["workspace"]),
            ],
        )
        assert result.exit_code == 0
        assert "Would save config" in result.output


class TestInit:
    """Tests for init command."""

    def test_creates_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Creates config file."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "init",
                "--code",
                str(test_env["code"]),
                "--workspace",
                str(test_env["workspace"]),
            ],
        )
        assert result.exit_code == 0
        assert test_env["config"].exists()
        assert "Config saved to" in result.output

    def test_creates_code_dir(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Creates code directory if it doesn't exist."""
        new_code = test_env["code"].parent / "new_code"
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "init",
                "--code",
                str(new_code),
                "--workspace",
                str(test_env["workspace"]),
            ],
        )
        assert result.exit_code == 0
        assert new_code.exists()

    def test_multiple_workspaces(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Supports multiple workspace directories."""
        ws2 = test_env["workspace"].parent / "workspace2"
        ws2.mkdir()

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "init",
                "--code",
                str(test_env["code"]),
                "--workspace",
                str(test_env["workspace"]),
                "--workspace",
                str(ws2),
            ],
        )
        assert result.exit_code == 0

        config = load_config(test_env["config"])
        assert len(config.workspaces) == 2

    def test_scan_repos_non_interactive(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Scans repos in non-interactive mode."""
        # Create a repo
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--non-interactive",
                "init",
                "--code",
                str(test_env["code"]),
                "--workspace",
                str(test_env["workspace"]),
                "--scan",
            ],
        )
        assert result.exit_code == 0
        assert "Found 1 repositories" in result.output

        config = load_config(test_env["config"])
        assert "my-repo" in config.all_repos()

    def test_warns_on_missing_dirs(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows warnings for missing directories."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "init",
                "--code",
                str(test_env["code"]),
                "--workspace",
                str(test_env["workspace"].parent / "nonexistent"),
            ],
        )
        assert result.exit_code == 0
        assert "Warning:" in result.output


class TestStatus:
    """Tests for status command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_all_synced(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows synced message when nothing to do."""
        # Create config
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Everything is in sync" in result.output

    def test_shows_uncategorized(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows uncategorized repos."""
        (test_env["code"] / "uncategorized-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Uncategorized repos" in result.output
        assert "uncategorized-repo" in result.output

    def test_shows_missing_repos(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows repos in config but not in code."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["missing-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Missing repos" in result.output
        assert "missing-repo" in result.output

    def test_shows_symlinks_to_create(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows symlinks that need to be created."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Symlinks to create" in result.output
        assert "my-repo" in result.output

    def test_root_category_display_without_dot(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Root category repos display without './' in path."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        # Should show "workspace/my-repo" not "workspace/./my-repo"
        assert "workspace/my-repo" in result.output
        assert "workspace/./my-repo" not in result.output

    def test_orphan_message_suggests_prune(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Status message mentions --prune when orphans exist."""
        # Create orphan symlink
        (test_env["workspace"] / "orphan").symlink_to(test_env["code"])

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Orphaned symlinks" in result.output
        assert "--prune" in result.output

    def test_shows_non_symlink_directories(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Shows directories in workspace that are not symlinks."""
        # Create a real directory (not a symlink) in workspace
        (test_env["workspace"] / "direct-clone" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Non-symlink directories" in result.output
        assert "direct-clone" in result.output

    def test_shows_symlink_conflicts(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Shows conflicts where directory exists where symlink should be."""
        # Create repo in code directory
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        # Create a directory (not a symlink) at the symlink target location
        (test_env["workspace"] / "my-repo").mkdir()
        (test_env["workspace"] / "my-repo" / "some-file.txt").write_text("conflict")

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "status",
            ],
        )
        assert result.exit_code == 0
        assert "Conflicts" in result.output
        assert "my-repo" in result.output


class TestApply:
    """Tests for apply command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_nothing_to_do(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows message when nothing to do."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 0
        assert "Nothing to do" in result.output

    def test_creates_symlinks(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Creates symlinks from config."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 0
        assert "Created 1 symlinks" in result.output
        assert (test_env["workspace"] / "my-repo").is_symlink()

    def test_creates_category_dirs(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Creates category directories for symlinks."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["vmware/vsphere"] = Category(path="vmware/vsphere", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 0
        assert (test_env["workspace"] / "vmware" / "vsphere" / "my-repo").is_symlink()

    def test_dry_run_no_changes(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Dry run doesn't create symlinks."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--dry-run",
                "apply",
            ],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert not (test_env["workspace"] / "my-repo").exists()

    def test_prune_orphans(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Removes orphaned symlinks with --prune."""
        # Create orphan symlink
        (test_env["workspace"] / "orphan").symlink_to(test_env["code"])

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
                "--prune",
            ],
        )
        assert result.exit_code == 0
        assert "Removed 1 symlinks" in result.output
        assert not (test_env["workspace"] / "orphan").exists()

    def test_refuses_with_category_repo_conflict(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Refuses to apply when category path conflicts with repo name."""
        # Create repo in code directory
        (test_env["code"] / "acme-project" / ".git").mkdir(parents=True)

        # Config with conflicting category/repo
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        # Repo "acme-project" in root category
        ws.categories["."] = Category(path=".", repos=["acme-project"])
        # Category "acme-project/git" conflicts with repo name
        ws.categories["acme-project/git"] = Category(
            path="acme-project/git", repos=["other-repo"]
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 1
        assert "Cannot apply" in result.output
        assert "config has errors" in result.output

    def test_refuses_with_symlink_conflicts(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Refuses to apply when directory exists where symlink should be."""
        # Create repo in code directory
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)
        # Create non-symlink directory in workspace where symlink should go
        (test_env["workspace"] / "my-repo").mkdir()

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
        )
        assert result.exit_code == 1
        assert "Cannot apply" in result.output
        assert "directory exists" in result.output.lower()

    def test_prompts_on_warnings(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Prompts user to continue when config has warnings."""
        # Create repo but use non-existent code path to trigger warning
        nonexistent_code = test_env["code"].parent / "nonexistent"

        config = Config(code_path=nonexistent_code)
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        # User declines to continue
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
            input="n\n",
        )
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "Continue?" in result.output

    def test_proceeds_on_warnings_when_confirmed(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Proceeds when user confirms despite warnings."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)
        # Use non-existent workspace to trigger warning
        nonexistent_ws = test_env["workspace"].parent / "nonexistent-ws"

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=nonexistent_ws)
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["nonexistent-ws"] = ws
        save_config(config, test_env["config"])

        # User confirms to continue
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "apply",
            ],
            input="y\n",
        )
        assert "Warning" in result.output
        assert "Continue?" in result.output

    def test_skips_prompt_in_non_interactive(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Skips warning prompt in non-interactive mode."""
        nonexistent_code = test_env["code"].parent / "nonexistent"

        config = Config(code_path=nonexistent_code)
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--non-interactive",
                "apply",
            ],
        )
        assert "Warning" in result.output
        assert "Continue?" not in result.output


class TestSync:
    """Tests for sync command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "sync",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_all_categorized(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows message when all repos categorized."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "sync",
            ],
        )
        assert result.exit_code == 0
        assert "All repos are categorized" in result.output

    def test_adds_uncategorized_non_interactive(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Adds uncategorized repos in non-interactive mode."""
        (test_env["code"] / "new-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--non-interactive",
                "sync",
            ],
        )
        assert result.exit_code == 0
        assert "new-repo" in result.output
        assert "Added 1 repos to config" in result.output

        # Verify config was updated
        config = load_config(test_env["config"])
        assert "new-repo" in config.all_repos()


class TestAdd:
    """Tests for add command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "add",
                "some-repo",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_repo_not_found(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if repo doesn't exist."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "add",
                "nonexistent",
            ],
        )
        assert result.exit_code == 1
        assert "Repo not found" in result.output

    def test_not_git_repo(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if directory is not a git repo."""
        (test_env["code"] / "not-git").mkdir()

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "add",
                "not-git",
            ],
        )
        assert result.exit_code == 1
        assert "Not a git repo" in result.output

    def test_adds_repo_non_interactive(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Adds repo in non-interactive mode."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--non-interactive",
                "add",
                "my-repo",
            ],
        )
        assert result.exit_code == 0
        assert "Added my-repo" in result.output

        # Verify config was updated
        config = load_config(test_env["config"])
        assert "my-repo" in config.all_repos()

    def test_adopts_repo_from_workspace(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Adopts a repo that exists in workspace but not in code."""
        # Create repo directly in workspace (not a symlink)
        (test_env["workspace"] / "direct-repo" / ".git").mkdir(parents=True)
        (test_env["workspace"] / "direct-repo" / "README.md").write_text("test")

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--non-interactive",
                "add",
                "direct-repo",
            ],
            input="y\n",  # Confirm move
        )
        assert result.exit_code == 0

        # Verify repo was moved to code directory
        assert (test_env["code"] / "direct-repo" / ".git").exists()
        assert (test_env["code"] / "direct-repo" / "README.md").exists()
        # Original should be gone (or be a symlink after apply)
        assert not (test_env["workspace"] / "direct-repo" / ".git").is_dir() or \
               (test_env["workspace"] / "direct-repo").is_symlink()

        # Verify config was updated
        config = load_config(test_env["config"])
        assert "direct-repo" in config.all_repos()


class TestValidate:
    """Tests for validate command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "validate",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_valid_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Reports success for valid config."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "validate",
            ],
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_reports_category_repo_conflict(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Reports category/repo path conflicts."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["acme-project"])
        ws.categories["acme-project/git"] = Category(
            path="acme-project/git", repos=["other-repo"]
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "validate",
            ],
        )
        assert result.exit_code == 1
        assert "conflict" in result.output.lower()

    def test_reports_symlink_conflicts(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Reports when directory exists where symlink should be."""
        # Create repo in code directory
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)
        # Create non-symlink directory in workspace
        (test_env["workspace"] / "my-repo").mkdir()

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "validate",
            ],
        )
        assert result.exit_code == 1
        assert "directory exists" in result.output.lower()


class TestFind:
    """Tests for find command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_no_repos(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows message when no repos configured."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
            ],
        )
        assert result.exit_code == 0
        assert "No repos" in result.output

    def test_list_mode_shows_matches(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """List mode shows matching repos without interactive prompt."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["tas-vcf", "tas-config", "other-repo"])
        ws.categories["vmware"] = Category(path="vmware", repos=["tas-tools"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
                "--list",
                "tas",
            ],
        )
        assert result.exit_code == 0
        assert "tas-vcf" in result.output
        assert "tas-config" in result.output
        assert "tas-tools" in result.output
        assert "other-repo" not in result.output

    def test_path_mode_outputs_path_only(
        self, runner: CliRunner, test_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path mode outputs only the selected path for cd."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        # Mock the fuzzy selector to return a selection
        def mock_fuzzy(*args, **kwargs):
            class MockPrompt:
                def execute(self):
                    return f"my-repo|workspace/my-repo|{test_env['workspace']}/my-repo"
            return MockPrompt()

        monkeypatch.setattr("gro.cli.inquirer.fuzzy", mock_fuzzy)

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
                "--path",
            ],
        )
        assert result.exit_code == 0
        # Should output only the path, no extra formatting
        assert result.output.strip() == str(test_env["workspace"] / "my-repo")

    def test_list_mode_without_pattern_shows_all(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """List mode without pattern shows all repos."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["repo-a", "repo-b"])
        ws.categories["nested"] = Category(path="nested", repos=["repo-c"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
                "--list",
            ],
        )
        assert result.exit_code == 0
        assert "repo-a" in result.output
        assert "repo-b" in result.output
        assert "repo-c" in result.output

    def test_nested_category_paths_correct(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Nested category paths are displayed and resolved correctly."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["vmware/cloud-foundry"] = Category(
            path="vmware/cloud-foundry", repos=["tas-vcf"]
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
                "--list",
                "tas",
            ],
        )
        assert result.exit_code == 0
        assert "tas-vcf" in result.output
        assert "workspace/vmware/cloud-foundry/tas-vcf" in result.output
        # Full path should include the nested structure (check parts due to line wrapping)
        assert "vmware/cloud-foundry/tas-vcf" in result.output

    def test_cancelled_selection_in_path_mode(
        self, runner: CliRunner, test_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cancelled selection in path mode exits with code 1."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", repos=["my-repo"])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        # Mock the fuzzy selector to return None (cancelled)
        def mock_fuzzy(*args, **kwargs):
            class MockPrompt:
                def execute(self):
                    return None
            return MockPrompt()

        monkeypatch.setattr("gro.cli.inquirer.fuzzy", mock_fuzzy)

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "find",
                "--path",
            ],
        )
        assert result.exit_code == 1
