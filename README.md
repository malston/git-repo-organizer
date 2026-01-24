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
    - govc # Creates symlink "govc"
    - acme-git:git # Creates symlink "git" -> acme-git repo
    - acme-stuff:stuff # Creates symlink "stuff" -> acme-stuff repo
```

This creates:

```
workspace/vendor/tools/
├── govc -> ../../../code/govc
├── git -> ../../../code/acme-git
└── stuff -> ../../../code/acme-stuff
```

## Commands

### `gro init`

Initialize configuration with code and workspace directories.

```bash
gro init --code ~/code --workspace ~/workspace
gro init --scan                    # Scan and categorize existing repos interactively
gro --non-interactive init --scan --by-org  # Auto-organize by git remote org
gro --non-interactive init --scan --by-org --include-domain  # Include domain in path
gro --non-interactive init --scan --auto-apply  # Auto-apply symlinks after init
```

The `--by-org` flag parses each repo's git remote to extract the org/owner and creates categories automatically. Use `--include-domain` for multi-host setups (e.g., GitHub + GitHub Enterprise).

The `--auto-apply` flag automatically creates symlinks after init, but only if there are no warnings or conflicts. If issues are detected, it skips apply and prompts you to run `gro apply` manually after resolving them.

**Example: Create a new workspace with auto-organization**

```bash
# Create a new config organized by org with domain paths and auto-apply symlinks
gro -c ~/.config/gro/config-by-org.yaml --non-interactive init --scan --by-org --include-domain --workspace ~/git --auto-apply

# Or without auto-apply, do it in steps:
gro -c ~/.config/gro/config-by-org.yaml init --scan --by-org --include-domain --workspace ~/git
gro -c ~/.config/gro/config-by-org.yaml -n apply  # Preview
gro -c ~/.config/gro/config-by-org.yaml apply     # Apply
```

This creates categories like `github.com/malston`, `github.enterprise.com/team`, etc.

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

**Shell function for quick navigation:**

Add this to your `~/.bashrc` or `~/.zshrc` to create a `gcd` command that jumps to repositories:

```bash
# Jump to a git repo managed by gro
gcd() {
  local dir
  dir=$(gro find --path "$@")
  if [[ -n "$dir" ]]; then
    cd "$dir"
  fi
}
```

Then use it like:

```bash
gcd             # Interactive selection, then cd to chosen repo
gcd vcf         # Filter by pattern, then cd to chosen repo
```

### `gro fmt`

Format the configuration file, sorting categories and repos alphabetically.

```bash
gro fmt        # Format config file
gro -n fmt     # Dry run - preview changes
```

### `gro cat`

Manage categories in workspaces.

```bash
gro cat ls                    # List all categories with repo counts
gro cat add vmware/vsphere    # Add new category to first workspace
gro cat add -w projects tools # Add category to specific workspace
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
