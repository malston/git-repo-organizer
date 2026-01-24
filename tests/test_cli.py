# ABOUTME: Integration tests for gro CLI commands.
# ABOUTME: Tests init, status, apply, sync, and add commands.
"""Tests for gro.cli."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from gro.cli import main
from gro.config import load_config, save_config
from gro.models import Category, Config, RepoEntry, Workspace


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

    def test_scan_by_org_organizes_repos(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Scan with --by-org organizes repos by git remote org."""
        import subprocess

        # Create repos with different orgs
        repo1 = test_env["code"] / "homelab"
        repo1.mkdir()
        subprocess.run(["git", "init"], cwd=repo1, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:malston/homelab.git"],
            cwd=repo1,
            capture_output=True,
        )

        repo2 = test_env["code"] / "other-project"
        repo2.mkdir()
        subprocess.run(["git", "init"], cwd=repo2, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:claudup/other-project.git"],
            cwd=repo2,
            capture_output=True,
        )

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
                "--by-org",
            ],
        )
        assert result.exit_code == 0

        config = load_config(test_env["config"])
        ws = config.workspaces["workspace"]

        # Repos should be organized by org
        assert "malston" in ws.categories
        assert "claudup" in ws.categories
        assert "homelab" in ws.categories["malston"].repo_names
        assert "other-project" in ws.categories["claudup"].repo_names

    def test_scan_by_org_with_domain(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Scan with --by-org --include-domain includes domain in category."""
        import subprocess

        # Create repos from different domains
        repo1 = test_env["code"] / "public-repo"
        repo1.mkdir()
        subprocess.run(["git", "init"], cwd=repo1, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:malston/public-repo.git"],
            cwd=repo1,
            capture_output=True,
        )

        repo2 = test_env["code"] / "internal-repo"
        repo2.mkdir()
        subprocess.run(["git", "init"], cwd=repo2, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.enterprise.com:malston/internal-repo.git"],
            cwd=repo2,
            capture_output=True,
        )

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
                "--by-org",
                "--include-domain",
            ],
        )
        assert result.exit_code == 0

        config = load_config(test_env["config"])
        ws = config.workspaces["workspace"]

        # Categories should include domain
        assert "github.com/malston" in ws.categories
        assert "github.enterprise.com/malston" in ws.categories
        assert "public-repo" in ws.categories["github.com/malston"].repo_names
        assert "internal-repo" in ws.categories["github.enterprise.com/malston"].repo_names

    def test_scan_by_org_no_remote_goes_to_root(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Repos without remotes go to root category when using --by-org."""
        import subprocess

        # Create a repo without a remote
        repo = test_env["code"] / "local-only"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)

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
                "--by-org",
            ],
        )
        assert result.exit_code == 0

        config = load_config(test_env["config"])
        ws = config.workspaces["workspace"]

        # Repo should be in root category
        assert "." in ws.categories
        assert "local-only" in ws.categories["."].repo_names

    def test_scan_by_org_creates_alias_when_dir_differs(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Creates alias when local dir name differs from remote repo name."""
        import subprocess

        # Create repo with different local name than remote
        repo = test_env["code"] / "my-dotfiles"  # Local name
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(
            # Remote name is "dotfiles"
            ["git", "remote", "add", "origin", "git@github.com:malston/dotfiles.git"],
            cwd=repo,
            capture_output=True,
        )

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
                "--by-org",
            ],
        )
        assert result.exit_code == 0

        config = load_config(test_env["config"])
        ws = config.workspaces["workspace"]

        # Should have entry with alias
        assert "malston" in ws.categories
        entries = ws.categories["malston"].entries
        assert len(entries) == 1
        assert entries[0].repo_name == "my-dotfiles"  # Local dir name
        assert entries[0].alias == "dotfiles"  # Remote repo name


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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="missing-repo")])
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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

    def test_shows_non_repo_directories(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Shows directories in code folder that are not git repos."""
        # Create a git repo
        (test_env["code"] / "real-repo" / ".git").mkdir(parents=True)

        # Create directories without .git (not repos)
        (test_env["code"] / "not-a-repo").mkdir()
        (test_env["code"] / "failed-clone").mkdir()

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
        assert "Non-repo directories" in result.output
        assert "not-a-repo" in result.output
        assert "failed-clone" in result.output


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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["vmware/vsphere"] = Category(
            path="vmware/vsphere", entries=[RepoEntry(repo_name="my-repo")]
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
        assert result.exit_code == 0
        assert (test_env["workspace"] / "vmware" / "vsphere" / "my-repo").is_symlink()

    def test_dry_run_no_changes(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Dry run doesn't create symlinks."""
        (test_env["code"] / "my-repo" / ".git").mkdir(parents=True)

        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="acme-project")])
        # Category "acme-project/git" conflicts with repo name
        ws.categories["acme-project/git"] = Category(
            path="acme-project/git", entries=[RepoEntry(repo_name="other-repo")]
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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

    def test_creates_symlink_automatically(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Creates symlink automatically after adding repo."""
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

        # Verify symlink was created automatically
        symlink_path = test_env["workspace"] / "my-repo"
        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == (test_env["code"] / "my-repo").resolve()


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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="acme-project")])
        ws.categories["acme-project/git"] = Category(
            path="acme-project/git", entries=[RepoEntry(repo_name="other-repo")]
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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


class TestFmt:
    """Tests for fmt command."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "fmt",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_formats_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Formats config file with sorted categories and repos."""
        # Create an unsorted config manually
        config_content = """\
code: {code}
workspaces:
- {workspace}
workspace:
  vmware/vsphere:
  - pyvmomi
  - acme-tools:tools
  .:
  - zebra-repo
  - alpha-repo
""".format(code=test_env["code"], workspace=test_env["workspace"])
        test_env["config"].write_text(config_content)

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "fmt",
            ],
        )
        assert result.exit_code == 0
        assert "Formatted" in result.output

        # Verify the formatted content
        formatted = test_env["config"].read_text()
        # Repos should be sorted alphabetically
        assert formatted.index("alpha-repo") < formatted.index("zebra-repo")
        # Categories should be sorted (. comes before vmware/vsphere)
        assert formatted.index(".:") < formatted.index("vmware/vsphere:")
        # Aliased repos should be sorted by their string representation
        assert formatted.index("acme-tools:tools") < formatted.index("pyvmomi")

    def test_dry_run_no_changes(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Dry run shows what would change but doesn't modify file."""
        config_content = """\
code: {code}
workspaces:
- {workspace}
workspace:
  .:
  - zebra-repo
  - alpha-repo
""".format(code=test_env["code"], workspace=test_env["workspace"])
        test_env["config"].write_text(config_content)
        original_content = test_env["config"].read_text()

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--dry-run",
                "fmt",
            ],
        )
        assert result.exit_code == 0
        assert "Would format" in result.output

        # File should be unchanged
        assert test_env["config"].read_text() == original_content

    def test_already_formatted(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Shows message when config is already formatted."""
        # Create a config using save_config (which produces formatted output)
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(
            path=".",
            entries=[RepoEntry(repo_name="alpha-repo"), RepoEntry(repo_name="zebra-repo")],
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "fmt",
            ],
        )
        assert result.exit_code == 0
        assert "already formatted" in result.output.lower()


class TestCat:
    """Tests for cat command group."""

    def test_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "ls",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_ls_empty(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Lists no categories when none exist."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "ls",
            ],
        )
        assert result.exit_code == 0
        assert "No categories" in result.output

    def test_ls_shows_categories(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Lists all categories across workspaces."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="repo1")])
        ws.categories["vmware/vsphere"] = Category(
            path="vmware/vsphere", entries=[RepoEntry(repo_name="pyvmomi")]
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "ls",
            ],
        )
        assert result.exit_code == 0
        assert "workspace" in result.output
        assert "." in result.output or "(root)" in result.output
        assert "vmware/vsphere" in result.output

    def test_ls_shows_repo_counts(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Lists categories with repo counts."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(
            path=".",
            entries=[RepoEntry(repo_name="repo1"), RepoEntry(repo_name="repo2")],
        )
        ws.categories["tools"] = Category(
            path="tools", entries=[RepoEntry(repo_name="tool1")]
        )
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "ls",
            ],
        )
        assert result.exit_code == 0
        # Should show repo counts
        assert "2" in result.output  # root has 2 repos
        assert "1" in result.output  # tools has 1 repo

    def test_add_no_config(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Fails if config doesn't exist."""
        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "add",
                "new-category",
            ],
        )
        assert result.exit_code == 1
        assert "Config not found" in result.output

    def test_add_creates_category(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Adds a new empty category."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "add",
                "vmware/vsphere",
            ],
        )
        assert result.exit_code == 0
        assert "Added" in result.output or "Created" in result.output

        # Verify config was updated
        config = load_config(test_env["config"])
        assert "vmware/vsphere" in config.workspaces["workspace"].categories

    def test_add_to_specific_workspace(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """Adds category to specific workspace with -w flag."""
        ws2 = test_env["workspace"].parent / "projects"
        ws2.mkdir()

        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        config.workspaces["projects"] = Workspace(path=ws2)
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "add",
                "-w",
                "projects",
                "personal",
            ],
        )
        assert result.exit_code == 0

        # Verify it was added to the correct workspace
        config = load_config(test_env["config"])
        assert "personal" in config.workspaces["projects"].categories
        assert "personal" not in config.workspaces["workspace"].categories

    def test_add_already_exists(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Shows message if category already exists."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["existing"] = Category(path="existing", entries=[])
        config.workspaces["workspace"] = ws
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "cat",
                "add",
                "existing",
            ],
        )
        assert result.exit_code == 0
        assert "already exists" in result.output.lower()

    def test_add_dry_run(self, runner: CliRunner, test_env: dict[str, Path]) -> None:
        """Dry run doesn't modify config."""
        config = Config(code_path=test_env["code"])
        config.workspaces["workspace"] = Workspace(path=test_env["workspace"])
        save_config(config, test_env["config"])

        result = runner.invoke(
            main,
            [
                "--config",
                str(test_env["config"]),
                "--dry-run",
                "cat",
                "add",
                "new-category",
            ],
        )
        assert result.exit_code == 0
        assert "Would" in result.output

        # Verify config was not modified
        config = load_config(test_env["config"])
        assert "new-category" not in config.workspaces["workspace"].categories


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
        ws.categories["."] = Category(
            path=".",
            entries=[
                RepoEntry(repo_name="tas-vcf"),
                RepoEntry(repo_name="tas-config"),
                RepoEntry(repo_name="other-repo"),
            ],
        )
        ws.categories["vmware"] = Category(
            path="vmware", entries=[RepoEntry(repo_name="tas-tools")]
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
        assert "tas-config" in result.output
        assert "tas-tools" in result.output
        assert "other-repo" not in result.output

    def test_path_mode_outputs_path_only(
        self, runner: CliRunner, test_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path mode outputs only the selected path for cd."""
        config = Config(code_path=test_env["code"])
        ws = Workspace(path=test_env["workspace"])
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
        ws.categories["."] = Category(
            path=".",
            entries=[RepoEntry(repo_name="repo-a"), RepoEntry(repo_name="repo-b")],
        )
        ws.categories["nested"] = Category(
            path="nested", entries=[RepoEntry(repo_name="repo-c")]
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
            path="vmware/cloud-foundry", entries=[RepoEntry(repo_name="tas-vcf")]
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
        ws.categories["."] = Category(path=".", entries=[RepoEntry(repo_name="my-repo")])
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
