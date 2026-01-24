# ABOUTME: Command-line interface for the git repository organizer.
# ABOUTME: Implements init, status, apply, sync, and add commands.
"""CLI for gro - Git Repository Organizer."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
from rich.console import Console

from gro.config import (
    create_default_config,
    get_default_config_path,
    load_config,
    save_config,
    validate_config,
)
from gro.models import Config
from gro.workspace import (
    apply_sync_plan,
    cleanup_empty_directories,
    create_sync_plan,
    scan_code_dir,
    scan_workspace_non_symlinks,
)

console = Console()


def format_symlink_path(ws_name: str, cat_path: str, repo_name: str) -> str:
    """Format a symlink path for display, omitting './' for root category."""
    if cat_path == ".":
        return f"{ws_name}/{repo_name}"
    return f"{ws_name}/{cat_path}/{repo_name}"


def find_repo_in_workspaces(
    config: Config, repo_name: str
) -> tuple[Path, str, str] | None:
    """
    Find a non-symlink repo directory in any workspace.

    Args:
        config: The configuration.
        repo_name: Name of the repo to find.

    Returns:
        Tuple of (path, workspace_name, category_path) if found, None otherwise.
    """
    for ws_name, workspace in config.workspaces.items():
        non_symlinks = scan_workspace_non_symlinks(workspace.path)
        for cat_path, dir_names in non_symlinks.items():
            if repo_name in dir_names:
                if cat_path == ".":
                    return (workspace.path / repo_name, ws_name, cat_path)
                return (workspace.path / cat_path / repo_name, ws_name, cat_path)
    return None


class Context:
    """Shared context for CLI commands."""

    def __init__(
        self,
        config_path: Path | None = None,
        dry_run: bool = False,
        non_interactive: bool = False,
    ) -> None:
        self.config_path = config_path or get_default_config_path()
        self.dry_run = dry_run
        self.non_interactive = non_interactive
        self._config: Config | None = None

    @property
    def config(self) -> Config:
        """Load config lazily."""
        if self._config is None:
            self._config = load_config(self.config_path)
        return self._config

    def has_config(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()


pass_context = click.make_pass_decorator(Context, ensure=True)


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    help="Path to config file",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Preview changes without making them",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Don't prompt, use defaults",
)
@click.pass_context
def main(
    ctx: click.Context,
    config: Path | None,
    dry_run: bool,
    non_interactive: bool,
) -> None:
    """GRO - Git Repository Organizer.

    Manage git repositories with symlinks via YAML configuration.
    """
    ctx.obj = Context(
        config_path=config,
        dry_run=dry_run,
        non_interactive=non_interactive,
    )


@main.command()
@click.option(
    "--code",
    type=click.Path(path_type=Path),
    help="Path to code directory (default: ~/code)",
)
@click.option(
    "--workspace",
    "-w",
    "workspaces",
    type=click.Path(path_type=Path),
    multiple=True,
    help="Path to workspace directory (can be repeated)",
)
@click.option(
    "--scan",
    is_flag=True,
    help="Scan existing repos and prompt for categorization",
)
@pass_context
def init(
    ctx: Context,
    code: Path | None,
    workspaces: tuple[Path, ...],
    scan: bool,
) -> None:
    """Initialize gro configuration.

    Creates a config file with the specified code and workspace directories.
    """
    if (
        ctx.has_config()
        and not ctx.non_interactive
        and not click.confirm(f"Config already exists at {ctx.config_path}. Overwrite?")
    ):
        console.print("[yellow]Aborted[/yellow]")
        return

    # Create default config
    workspace_list = list(workspaces) if workspaces else None
    config = create_default_config(code_path=code, workspace_paths=workspace_list)

    # Create code directory if needed
    if not config.code_path.exists():
        if ctx.dry_run:
            console.print(f"[blue]Would create:[/blue] {config.code_path}")
        else:
            config.code_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created:[/green] {config.code_path}")

    # Scan existing repos if requested
    if scan and config.code_path.exists():
        repos = scan_code_dir(config.code_path)
        if repos:
            console.print(f"\nFound {len(repos)} repositories in {config.code_path}")

            if not ctx.non_interactive:
                for repo in repos:
                    categorize_repo_interactive(config, repo)
            else:
                # Add all to root category of first workspace
                if config.workspaces:
                    first_ws = next(iter(config.workspaces.values()))
                    category = first_ws.get_or_create_category(".")
                    category.repos.extend(repos)
                    console.print(f"Added {len(repos)} repos to '{first_ws.name}' workspace")

    # Save config
    if ctx.dry_run:
        console.print(f"\n[blue]Would save config to:[/blue] {ctx.config_path}")
    else:
        save_config(config, ctx.config_path)
        console.print(f"\n[green]Config saved to:[/green] {ctx.config_path}")

    # Show warnings
    warnings = validate_config(config)
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@main.command()
@pass_context
def status(ctx: Context) -> None:
    """Show status of repositories and symlinks."""
    if not ctx.has_config():
        console.print(f"[red]Config not found:[/red] {ctx.config_path}")
        console.print("Run 'gro init' to create a config file.")
        raise SystemExit(1)

    config = ctx.config
    plan = create_sync_plan(config)

    # Show uncategorized repos
    if plan.repos_to_add:
        console.print("\n[bold]Uncategorized repos in code directory:[/bold]")
        for repo in plan.repos_to_add:
            console.print(f"  [yellow]?[/yellow] {repo}")

    # Show missing repos
    if plan.repos_missing:
        console.print("\n[bold]Missing repos (in config but not in code):[/bold]")
        for repo in plan.repos_missing:
            console.print(f"  [red]![/red] {repo}")

    # Show symlinks to create
    if plan.symlinks_to_create:
        console.print("\n[bold]Symlinks to create:[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_create:
            console.print(f"  [green]+[/green] {format_symlink_path(ws_name, cat_path, repo_name)}")

    # Show symlinks to update
    if plan.symlinks_to_update:
        console.print("\n[bold]Symlinks to update:[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_update:
            console.print(f"  [blue]~[/blue] {format_symlink_path(ws_name, cat_path, repo_name)}")

    # Show orphaned symlinks
    if plan.symlinks_to_remove:
        console.print("\n[bold]Orphaned symlinks (not in config):[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_remove:
            console.print(f"  [red]-[/red] {format_symlink_path(ws_name, cat_path, repo_name)}")

    # Show symlink conflicts (directory exists where symlink should be)
    if plan.symlink_conflicts:
        console.print("\n[bold]Conflicts (directory exists where symlink should be):[/bold]")
        for ws_name, cat_path, repo_name in plan.symlink_conflicts:
            console.print(f"  [red]![/red] {format_symlink_path(ws_name, cat_path, repo_name)}")

    # Show non-symlink directories
    if plan.non_symlink_dirs:
        console.print("\n[bold]Non-symlink directories in workspace:[/bold]")
        for ws_name, cat_path, dir_name in plan.non_symlink_dirs:
            console.print(f"  [yellow]?[/yellow] {format_symlink_path(ws_name, cat_path, dir_name)}")

    # Summary
    if not plan.has_changes and not plan.has_warnings:
        console.print("\n[green]Everything is in sync![/green]")
    elif plan.has_changes:
        if plan.symlinks_to_remove:
            console.print("\n[yellow]Run 'gro apply --prune' to sync symlinks[/yellow]")
        else:
            console.print("\n[yellow]Run 'gro apply' to sync symlinks[/yellow]")


@main.command()
@click.option(
    "--prune",
    is_flag=True,
    help="Remove orphaned symlinks",
)
@click.option(
    "--workspace",
    "-w",
    "workspace_name",
    help="Only apply to specific workspace",
)
@pass_context
def apply(ctx: Context, prune: bool, workspace_name: str | None) -> None:
    """Apply configuration - create/update symlinks."""
    if not ctx.has_config():
        console.print(f"[red]Config not found:[/red] {ctx.config_path}")
        raise SystemExit(1)

    config = ctx.config
    plan = create_sync_plan(config)

    if not plan.has_changes:
        console.print("[green]Nothing to do - everything is in sync![/green]")
        return

    # Filter by workspace if specified
    if workspace_name:
        plan.symlinks_to_create = [
            x for x in plan.symlinks_to_create if x[0] == workspace_name
        ]
        plan.symlinks_to_update = [
            x for x in plan.symlinks_to_update if x[0] == workspace_name
        ]
        plan.symlinks_to_remove = [
            x for x in plan.symlinks_to_remove if x[0] == workspace_name
        ]

    # Show what will be done
    if plan.symlinks_to_create:
        console.print("\n[bold]Creating symlinks:[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_create:
            console.print(f"  [green]+[/green] {format_symlink_path(ws_name, cat_path, repo_name)}")

    if plan.symlinks_to_update:
        console.print("\n[bold]Updating symlinks:[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_update:
            console.print(f"  [blue]~[/blue] {format_symlink_path(ws_name, cat_path, repo_name)}")

    if prune and plan.symlinks_to_remove:
        console.print("\n[bold]Removing orphaned symlinks:[/bold]")
        for ws_name, cat_path, repo_name in plan.symlinks_to_remove:
            console.print(f"  [red]-[/red] {format_symlink_path(ws_name, cat_path, repo_name)}")

    if ctx.dry_run:
        console.print("\n[blue]Dry run - no changes made[/blue]")
        return

    # Apply changes
    results = apply_sync_plan(
        config,
        plan,
        dry_run=ctx.dry_run,
        remove_orphans=prune,
    )

    # Clean up empty directories
    for workspace in config.workspaces.values():
        cleanup_empty_directories(workspace.path, dry_run=ctx.dry_run)

    # Show results
    if results["created"]:
        console.print(f"\n[green]Created {len(results['created'])} symlinks[/green]")
    if results["updated"]:
        console.print(f"[blue]Updated {len(results['updated'])} symlinks[/blue]")
    if results["removed"]:
        console.print(f"[yellow]Removed {len(results['removed'])} symlinks[/yellow]")
    if results["errors"]:
        console.print("\n[red]Errors:[/red]")
        for error in results["errors"]:
            console.print(f"  {error}")


@main.command()
@click.option(
    "--workspace",
    "-w",
    "workspace_name",
    help="Only sync specific workspace",
)
@pass_context
def sync(ctx: Context, workspace_name: str | None) -> None:
    """Sync config with current workspace state.

    Scans code directory and updates config with any uncategorized repos.
    """
    if not ctx.has_config():
        console.print(f"[red]Config not found:[/red] {ctx.config_path}")
        console.print("Run 'gro init' to create a config file.")
        raise SystemExit(1)

    config = ctx.config
    repos_in_code = set(scan_code_dir(config.code_path))
    repos_in_config = config.all_repos()

    uncategorized = repos_in_code - repos_in_config

    if not uncategorized:
        console.print("[green]All repos are categorized![/green]")
        return

    console.print(f"\nFound {len(uncategorized)} uncategorized repos:\n")

    added_count = 0
    for repo in sorted(uncategorized):
        if ctx.non_interactive:
            # Add to root category of first workspace
            if config.workspaces:
                ws_name = workspace_name or next(iter(config.workspaces.keys()))
                workspace = config.workspaces.get(ws_name)
                if workspace:
                    category = workspace.get_or_create_category(".")
                    category.repos.append(repo)
                    console.print(f"  [green]+[/green] {repo} -> {ws_name}/.")
                    added_count += 1
        else:
            if categorize_repo_interactive(config, repo):
                added_count += 1

    if added_count > 0:
        if ctx.dry_run:
            console.print(f"\n[blue]Would add {added_count} repos to config[/blue]")
        else:
            save_config(config, ctx.config_path)
            console.print(f"\n[green]Added {added_count} repos to config[/green]")
            console.print("[yellow]Run 'gro apply' to create symlinks[/yellow]")


@main.command()
@click.argument("repo_name")
@pass_context
def add(ctx: Context, repo_name: str) -> None:
    """Add a repository to a category.

    Interactively select workspace and category for the repo.
    If the repo exists in a workspace but not in the code directory,
    offers to move it to the code directory first.
    """
    if not ctx.has_config():
        console.print(f"[red]Config not found:[/red] {ctx.config_path}")
        raise SystemExit(1)

    config = ctx.config
    suggested_ws: str | None = None
    suggested_cat: str | None = None

    # Check repo exists in code directory
    repo_path = config.code_path / repo_name
    if not repo_path.exists():
        # Check if it exists in a workspace as a non-symlink directory
        found = find_repo_in_workspaces(config, repo_name)
        if found:
            workspace_path, suggested_ws, suggested_cat = found
            console.print(f"Found '{repo_name}' in workspace: {workspace_path}")
            console.print(f"It should be moved to: {repo_path}")
            if click.confirm("Move to code directory?"):
                if ctx.dry_run:
                    console.print(f"[blue]Would move {workspace_path} -> {repo_path}[/blue]")
                else:
                    shutil.move(str(workspace_path), str(repo_path))
                    console.print(f"[green]Moved to {repo_path}[/green]")
            else:
                console.print("[yellow]Aborted[/yellow]")
                return
        else:
            console.print(f"[red]Repo not found:[/red] {repo_path}")
            raise SystemExit(1)

    if not (repo_path / ".git").exists():
        console.print(f"[red]Not a git repo:[/red] {repo_path}")
        raise SystemExit(1)

    # Check if already categorized
    locations = config.find_repo_locations(repo_name)
    if locations:
        console.print(f"Repo '{repo_name}' already in:")
        for ws_name, cat_path in locations:
            console.print(f"  - {ws_name}/{cat_path}")
        if not click.confirm("Add to another location?"):
            return

    if ctx.non_interactive:
        # Use suggested workspace/category or default to root of first workspace
        if config.workspaces:
            ws_name = suggested_ws or next(iter(config.workspaces.keys()))
            workspace = config.workspaces[ws_name]
            cat_path = suggested_cat or "."
            category = workspace.get_or_create_category(cat_path)
            category.repos.append(repo_name)
            console.print(f"Added {repo_name} to {format_symlink_path(ws_name, cat_path, repo_name)}")
    else:
        categorize_repo_interactive(config, repo_name, suggested_ws, suggested_cat)

    if ctx.dry_run:
        console.print("[blue]Dry run - config not saved[/blue]")
    else:
        save_config(config, ctx.config_path)
        console.print("[green]Config updated[/green]")
        console.print("[yellow]Run 'gro apply' to create symlinks[/yellow]")


def categorize_repo_interactive(
    config: Config,
    repo_name: str,
    suggested_ws: str | None = None,
    suggested_cat: str | None = None,
) -> bool:
    """
    Interactively categorize a repo.

    Args:
        config: The configuration to update.
        repo_name: Name of the repo.
        suggested_ws: Suggested workspace name (used as default).
        suggested_cat: Suggested category path (used as default).

    Returns:
        True if repo was categorized, False if skipped.
    """
    console.print(f"\n[bold]{repo_name}[/bold]")

    # Select workspace
    ws_names = list(config.workspaces.keys())
    if not ws_names:
        console.print("[red]No workspaces configured[/red]")
        return False

    if len(ws_names) == 1:
        ws_name = ws_names[0]
    else:
        console.print("Workspaces:")
        default_ws_idx = "1"
        for i, name in enumerate(ws_names, 1):
            marker = " (suggested)" if name == suggested_ws else ""
            console.print(f"  {i}. {name}{marker}")
            if name == suggested_ws:
                default_ws_idx = str(i)
        console.print("  s. Skip")

        choice = click.prompt("Select workspace", default=default_ws_idx)
        if choice.lower() == "s":
            return False

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ws_names):
                ws_name = ws_names[idx]
            else:
                console.print("[yellow]Invalid choice, skipping[/yellow]")
                return False
        except ValueError:
            console.print("[yellow]Invalid choice, skipping[/yellow]")
            return False

    workspace = config.workspaces[ws_name]

    # Get existing categories
    existing_cats = sorted(workspace.categories.keys())

    # Determine default choice for category
    default_cat_choice = "n"
    if suggested_cat and suggested_cat != ".":
        # Check if suggested category exists or should be created
        if suggested_cat in existing_cats:
            default_cat_choice = str(existing_cats.index(suggested_cat) + 1)
        else:
            # Will create new category with suggested name
            default_cat_choice = "n"

    if existing_cats:
        console.print("\nExisting categories:")
        for i, cat in enumerate(existing_cats, 1):
            display = cat if cat != "." else ". (root)"
            marker = " (suggested)" if cat == suggested_cat else ""
            console.print(f"  {i}. {display}{marker}")

    console.print("  n. New category")
    console.print("  s. Skip")

    choice = click.prompt("Select category", default=default_cat_choice)
    if choice.lower() == "s":
        return False

    if choice.lower() == "n":
        default_new_cat = suggested_cat if suggested_cat and suggested_cat != "." else "."
        cat_path = click.prompt("Category path (e.g., 'vmware/vsphere' or '.')", default=default_new_cat)
    else:
        try:
            idx = int(choice) - 1
            cat_path = existing_cats[idx] if 0 <= idx < len(existing_cats) else "."
        except ValueError:
            cat_path = "."

    # Add repo to category
    category = workspace.get_or_create_category(cat_path)
    if repo_name not in category.repos:
        category.repos.append(repo_name)
        console.print(f"  [green]+[/green] Added to {ws_name}/{cat_path}")
        return True
    else:
        console.print(f"  [yellow]Already in {ws_name}/{cat_path}[/yellow]")
        return False


if __name__ == "__main__":
    main()
