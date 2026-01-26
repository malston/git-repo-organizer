# Adopt Existing Workspace Symlinks

## Problem

When running `gro init` with an existing workspace that has symlinks pointing to `~/code`, the command creates an empty config with no categories. If a user accidentally deletes their config, there's no way to recover the category structure from existing symlinks.

## Solution

Enhance `--scan` on `init` and the `sync` command to detect and adopt existing workspace symlinks.

## Behavior

### Symlink Adoption Logic

1. For each symlink in the workspace:
   - Resolve the symlink target
   - Check if target is inside the code directory
   - If yes: extract repo name, determine if alias needed, add to config
   - If no: warn and skip

2. The symlink's directory path within the workspace becomes the category path
   - `~/workspace/tools/git` -> category `tools`
   - `~/workspace/foo` -> category `.` (root)

3. If symlink name differs from repo name, record as `repo_name:alias`
   - Symlink `git` -> `~/code/acme-code` becomes config entry `acme-code:git`

### Command Changes

| Command       | Current Behavior                       | New Behavior                                  |
| ------------- | -------------------------------------- | --------------------------------------------- |
| `init --scan` | Scans code dir, prompts for categories | Also adopts existing workspace symlinks first |
| `sync`        | Finds uncategorized repos in code dir  | Also adopts orphaned workspace symlinks       |

### Output

```
Adopting existing symlinks:
  + workspace/tools/git -> acme-code (alias: git)
  + workspace/vmware/pyvmomi -> pyvmomi
  ! Skipping external/tool -> /opt/tools/tool (not in code directory)
```

## Implementation

### New Function

```python
# workspace.py
def adopt_workspace_symlinks(
    workspace: Workspace,
    code_path: Path,
) -> tuple[list[tuple[str, RepoEntry]], list[str]]:
    """
    Scan workspace and return symlinks that point to code directory.

    Returns:
        - List of (category_path, RepoEntry) to add
        - List of warning messages for skipped symlinks
    """
```

### Changes to `init --scan`

Before scanning code dir for repos to categorize:

1. Call `adopt_workspace_symlinks()` for each workspace
2. Add returned entries to config
3. Print warnings for skipped symlinks
4. Continue with existing code-dir scan (skips already-added repos)

### Changes to `sync`

After finding uncategorized repos in code dir:

1. Scan workspaces for symlinks not in config
2. For each orphaned symlink pointing to code dir:
   - If repo already in config elsewhere: skip
   - If repo not in config: adopt with current category/alias
3. Print warnings for non-code-dir symlinks

## Test Cases

### Unit tests for `adopt_workspace_symlinks()`

1. Basic adoption - symlink `foo` -> `~/code/foo` becomes entry `foo`
2. Alias detection - symlink `git` -> `~/code/acme-code` becomes `acme-code:git`
3. Nested categories - symlink at `tools/cli/git` -> category path `tools/cli`
4. Skip non-code symlinks - symlink -> `/opt/elsewhere` produces warning
5. Broken symlinks - target doesn't exist, skip with warning

### Integration tests for `init --scan`

1. Empty workspace + repos in code -> prompts for categorization (existing)
2. Workspace with symlinks + no config -> adopts symlinks first
3. Mixed scenario - some symlinks, some uncategorized repos

### Integration tests for `sync`

1. Orphaned symlinks (in workspace but not config) -> adopted
2. Symlinks already in config -> skipped (no duplicates)
3. Non-code-dir symlinks -> warning, not adopted
