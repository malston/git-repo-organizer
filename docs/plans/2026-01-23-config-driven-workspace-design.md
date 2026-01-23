# Config-Driven Workspace Organizer Design

## Overview

Replace the bash-based migration scripts with a Python CLI (`gro`) that manages git repositories through a YAML configuration file. Repos are cloned to a flat `code` directory and symlinked into one or more organized `workspace` directories.

## Directory Model

**Two distinct directory types:**

| Directory      | Purpose                                                       |
| -------------- | ------------------------------------------------------------- |
| `code`         | Single directory where all repos are cloned (flat structure)  |
| `workspace(s)` | One or more directories where symlinks create organized views |

**Example structure:**

```
~/code/                              # Actual repos (flat, untouched)
├── vcf-offline-depot/
├── claude-mem/
├── wellsfargo-stuff/
└── hello-world/

~/workspace/                         # Organized symlinks
├── my-dotfiles -> ~/code/my-dotfiles
├── vmware/vsphere/vcf-offline-depot -> ~/code/vcf-offline-depot
└── ai/claude/claude-mem -> ~/code/claude-mem

~/projects/                          # Another organized view
├── quick-script -> ~/code/quick-script
├── work/wellsfargo-stuff -> ~/code/wellsfargo-stuff
└── demos/hello-world -> ~/code/hello-world

~/.config/gro/config.yaml            # Configuration file
```

## Configuration File

**Location:** `~/.config/gro/config.yaml`

**Schema:**

```yaml
code: ~/code

workspaces:
  - ~/workspace
  - ~/projects

workspace: # Categories for ~/workspace (basename of path)
  .: # "." = symlink directly to workspace root
    - my-dotfiles
  vmware/vsphere:
    - vcf-offline-depot
  ai/claude:
    - claude-mem
    - hello-world # Same repo can appear in multiple workspaces

projects: # Categories for ~/projects
  .:
    - quick-script
  work:
    - wellsfargo-stuff
  demos:
    - hello-world # Same repo symlinked here too
```

**Rules:**

- `code` specifies where actual repos live (flat)
- `workspaces` lists all managed workspace directories
- Each workspace gets a top-level key matching its directory basename
- `.` category means symlink directly to workspace root (no subfolder)
- Same repo can appear in multiple workspaces (multiple symlinks to same source)
- Same repo can appear in multiple categories within a workspace
- Repos in `code/` but not in any category have no symlinks

## CLI Commands

### `gro init`

Create configuration file with specified paths.

```bash
gro init                                    # Defaults: code=~/code, workspace=~/workspace
gro init --code ~/code --workspace ~/work   # Custom paths
gro init --workspace ~/projects             # Add additional workspace
gro init --scan                             # Scan code dir and prompt for categorization
```

### `gro sync`

Regenerate config from current workspace state.

```bash
gro sync                      # Interactive - prompts for uncategorized repos
gro sync --non-interactive    # Adds uncategorized repos to "." category
gro sync --workspace projects # Only sync one workspace
```

**Behavior:**

- Scans `code` directory for all git repos
- For repos not in config: prompts for workspace and category (interactive) or adds to `.` (non-interactive)
- For config entries pointing to non-existent repos: warns but keeps entry

### `gro apply`

Create/update symlinks to match configuration.

```bash
gro apply                     # Apply all changes
gro apply --dry-run           # Preview only
gro apply --workspace projects # Only apply to one workspace
```

**Behavior:**

- Creates workspace and category directories as needed
- Creates symlinks for all configured repos
- Updates symlinks that point to wrong location
- Removes orphaned symlinks (symlinks not in config)

### `gro status`

Show differences between config and actual state.

```bash
gro status
```

**Shows:**

- Repos in `code/` not in any workspace category
- Config entries pointing to non-existent repos
- Symlinks that don't match config
- Orphaned symlinks (exist but not in config)

### `gro add <repo>`

Interactively add a repo to a category.

```bash
gro add hello-world           # Prompts for workspace and category
```

## Common Flags

| Flag                 | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| `--config <path>`    | Override config location (default: `~/.config/gro/config.yaml`) |
| `--dry-run`, `-n`    | Preview changes without making them                             |
| `--non-interactive`  | Don't prompt, use defaults                                      |
| `--workspace <name>` | Operate on specific workspace only                              |

## Error Handling

| Situation                                       | Behavior                                  |
| ----------------------------------------------- | ----------------------------------------- |
| Repo in config doesn't exist in `code/`         | Warn, keep in config                      |
| Repo in `code/` not in any category             | `sync` prompts or adds to `.`             |
| Category dir has real file/folder (not symlink) | Error, suggest resolution                 |
| Symlink exists but points elsewhere             | `apply` updates it                        |
| `code` directory doesn't exist                  | `init` creates it; other commands error   |
| `workspace` directory doesn't exist             | `apply` creates it                        |
| Invalid YAML in config                          | Error with line number                    |
| Workspace basename collision                    | Error (e.g., two paths ending in `/work`) |

## Implementation

**Language:** Python 3.10+

**Dependencies:**

- `click` or `typer` for CLI
- `pyyaml` for config parsing
- `rich` for terminal output (optional, for nice tables/colors)

**File structure:**

```
gro/
├── __init__.py
├── __main__.py          # Entry point
├── cli.py               # Click/typer command definitions
├── config.py            # Config loading/saving/validation
├── workspace.py         # Workspace scanning and symlink operations
└── models.py            # Data classes for Repo, Workspace, Category
```

**Installation:**

```bash
pip install -e .         # Editable install
# or
pipx install .           # Isolated install
```

## Example Workflow

```bash
# Initial setup
gro init --code ~/code --workspace ~/workspace --workspace ~/projects

# Clone some repos
cd ~/code
git clone git@github.com:foo/bar.git
git clone git@github.com:baz/qux.git

# Sync to discover new repos
gro sync
# Prompts: "bar" is not categorized. Which workspace? [workspace/projects]
# Prompts: "bar" category? [./ai/tools/...]

# Apply the config
gro apply

# Check status anytime
gro status

# Quick add without full sync
gro add qux
gro apply
```

## Migration from Current Scripts

The existing bash scripts (`analyze_repos.sh`, `migrate_repos.sh`, etc.) will be deprecated. A one-time migration path:

1. Run `gro init --scan` to generate initial config from existing repos
2. Edit `config.yaml` to organize categories as desired
3. Run `gro apply` to create the symlink structure
4. Verify everything works
5. Remove old bash scripts

## Future Considerations (Out of Scope)

- Workspace directory migration (changing `~/workspace` to `~/work`)
- Git clone integration (`gro clone <url>`)
- Remote config sync (store config in a git repo)
- Multiple code directories
