# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gro (Git Repository Organizer) is a Python CLI tool that manages git repositories via symlinks. Repos are cloned flat to a `code` directory (e.g., `~/code`) and symlinked into workspace directories organized by categories.

## Common Commands

```bash
# Install dependencies
make dev

# Run tests with coverage
make test

# Run single test file
uv run pytest tests/test_models.py -v

# Run single test
uv run pytest tests/test_cli.py::TestInit::test_creates_config -v

# Run all checks (lint, typecheck, test)
make check

# Format code
make format

# Fix lint issues
make lint-fix

# Run the CLI
uv run gro status
uv run gro --help
```

## Architecture

### Data Flow

1. **Config** (`~/.config/gro/config.yaml`) defines which repos belong to which categories in each workspace
2. **Code directory** (e.g., `~/code`) contains the actual git repos, stored flat
3. **Workspace directories** (e.g., `~/workspace`) contain symlinks organized by category pointing back to code directory

### Module Structure

- `models.py` - Dataclasses: `Config`, `Workspace`, `Category`, `RepoEntry`, `RepoStatus`, `SyncPlan`
- `config.py` - YAML loading/saving, path expansion (`~` handling), validation
- `workspace.py` - Symlink operations: scan, create, update, remove; sync planning
- `cli.py` - Click CLI with commands: `init`, `status`, `validate`, `apply`, `sync`, `add`, `find`, `fmt`, `cat`

### Key Concepts

- **Category path "."** means symlinks at workspace root (no subdirectory)
- **Repos can exist in multiple workspaces** - no restriction on where a repo is symlinked
- **Workspace name** is derived from directory basename (e.g., `/home/user/workspace` → `workspace`)
- **Symlinks are relative** (e.g., `../code/repo-name`) for portability
- **Aliased symlinks** - Use `repo_name:alias` syntax to create symlinks with different names than the repo

## Config Format

```yaml
code: ~/code
workspaces:
  - ~/workspace
workspace: # Categories for "workspace"
  .: # Root category - symlinks directly to workspace/
    - repo1
    - acme-git:git # Creates symlink "git" -> acme-git repo
  vmware/vsphere: # Nested category - workspace/vmware/vsphere/
    - pyvmomi
    - acme-tools:tools # Creates symlink "tools" -> acme-tools repo
```

### Aliased Symlinks

Use `repo_name:alias` syntax to create symlinks with different names than the repository:

```yaml
vendor/projects:
  - govc # Creates symlink "govc"
  - acme-git:git # Creates symlink "git" pointing to acme-git repo
  - acme-stuff:stuff # Creates symlink "stuff" pointing to acme-stuff repo
```

This creates:

```
workspace/vendor/projects/
├── govc -> ../../../code/govc
├── git -> ../../../code/acme-git
└── stuff -> ../../../code/acme-stuff
```

## CLI Commands

- `gro init` - Initialize config file
  - `--scan` - Scan repos and prompt for categorization
  - `--by-org` - Organize by git remote org (auto-categorize)
  - `--include-domain` - Include domain in category path
- `gro status` - Show sync status (uncategorized repos, missing symlinks, conflicts)
- `gro validate` - Check config for errors without making changes
- `gro apply` - Create/update symlinks (blocks on errors, prompts on warnings)
- `gro sync` - Add uncategorized repos to config interactively
- `gro add <repo>` - Add a specific repo to a category (can adopt from workspace)
- `gro find [pattern]` - Interactive fuzzy search for repos
  - `--list` - Print matches without interactive selection
  - `--path` - Output only path (for `cd "$(gro find --path)"`)
- `gro fmt` - Format config file (sorts categories and repos alphabetically)
- `gro cat ls` - List all categories with repo counts
- `gro cat add <path>` - Add a new category (`-w` to specify workspace)

All commands support `-h` for help.

## Validation

gro validates configs and blocks dangerous operations:

**Errors (blocks `apply`):**

- Category/repo path conflicts (e.g., repo "foo" in root + category "foo/bar")
- Directory exists where symlink should be created

**Warnings (prompts in `apply`):**

- Code directory doesn't exist
- Workspace directory doesn't exist

Run `gro validate` to check config without applying changes.

## Testing

Tests use pytest with fixtures. CLI tests use `click.testing.CliRunner`. All workspace/symlink tests use `tmp_path` fixture for isolation.
