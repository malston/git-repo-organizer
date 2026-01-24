# gro - Git Repository Organizer

A CLI tool for managing git repositories with symlinks via YAML configuration.

## Overview

gro helps you organize your git repositories by:

- Keeping all repos cloned flat in a single `code` directory
- Creating symlinks in workspace directories organized by categories
- Managing multiple workspaces with independent category structures

## Installation

```bash
# Clone the repo
git clone https://github.com/malston/git-repo-organizer.git
cd git-repo-organizer

# Install with uv
uv sync

# Or install globally
uv tool install .
```

## Quick Start

```bash
# Initialize configuration
gro init --code ~/code --workspace ~/workspace

# Scan existing repos and categorize them
gro sync

# Create symlinks from config
gro apply

# Check status
gro status
```

## Configuration

Config file is stored at `~/.config/gro/config.yaml`:

```yaml
code: ~/code

workspaces:
  - ~/workspace
  - ~/projects

workspace:
  .: [repo1, repo2] # Symlinks at workspace root
  vmware:
    - vsphere-automation
    - govmomi
  vmware/vsphere:
    - pyvmomi

projects:
  personal: [my-app, dotfiles]
```

### Aliased Symlinks

Use `repo_name:alias` syntax to create symlinks with different names:

```yaml
workspace:
  vendor/tools:
    - config-lab # Creates symlink "config-lab"
    - acme-git:git # Creates symlink "git" -> acme-git repo
    - acme-stuff:stuff # Creates symlink "stuff" -> acme-stuff repo
```

This creates:

```
workspace/vendor/tools/
├── config-lab -> ../../../code/config-lab
├── git -> ../../../code/acme-git
└── stuff -> ../../../code/acme-stuff
```

## Commands

### `gro init`

Initialize configuration with code and workspace directories.

```bash
gro init --code ~/code --workspace ~/workspace
gro init --scan  # Also scan and categorize existing repos
```

### `gro status`

Show sync status of repositories and symlinks.

```bash
gro status
```

### `gro apply`

Create/update symlinks based on configuration.

```bash
gro apply           # Create missing symlinks
gro apply --prune   # Also remove orphaned symlinks
gro -n apply        # Dry run - preview changes
```

### `gro sync`

Add uncategorized repos from code directory to config.

```bash
gro sync                    # Interactive categorization
gro --non-interactive sync  # Add all to root category
```

### `gro add <repo>`

Add a specific repository to a category.

```bash
gro add my-new-repo
```

### `gro validate`

Check configuration for errors without making changes.

```bash
gro validate
```

### `gro find [pattern]`

Interactive fuzzy search for repositories.

```bash
gro find              # Interactive selection of all repos
gro find vcf          # Filter repos matching "vcf"
gro find --list       # Print matches without interactive selection
gro find --path vcf   # Output only path (useful for cd)

# Change to a repo directory
cd "$(gro find --path)"
```

### `gro fmt`

Format the configuration file, sorting categories and repos alphabetically.

```bash
gro fmt        # Format config file
gro -n fmt     # Dry run - preview changes
```

## Common Options

- `--config/-c PATH` - Use custom config file
- `--dry-run/-n` - Preview changes without making them
- `--non-interactive` - Use defaults without prompts

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run all checks (lint, typecheck, test)
make check

# Format code
make format
```

## License

MIT
