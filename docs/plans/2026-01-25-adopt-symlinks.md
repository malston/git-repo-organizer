# Adopt Symlinks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable `init --scan` and `sync` to adopt existing workspace symlinks into the config.

**Architecture:** Add `adopt_workspace_symlinks()` function to workspace.py that scans a workspace for symlinks pointing to the code directory, returning entries with proper aliases. Integrate into init and sync commands.

**Tech Stack:** Python, Click CLI, pytest

---

## Task 1: Add `adopt_workspace_symlinks` Function

**Files:**

- Modify: `src/gro/workspace.py` (add new function after `scan_workspace_symlinks`)
- Test: `tests/test_workspace.py`

**Step 1: Write failing test for basic adoption**

Add to `tests/test_workspace.py`:

```python
class TestAdoptWorkspaceSymlinks:
    """Tests for adopt_workspace_symlinks function."""

    def test_basic_adoption(self, tmp_path: Path) -> None:
        """Adopts symlink pointing to code directory."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "my-repo").mkdir()
        (code_path / "my-repo" / ".git").mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "my-repo").symlink_to(code_path / "my-repo")

        workspace = Workspace(path=workspace_path)
        entries, warnings = adopt_workspace_symlinks(workspace, code_path)

        assert len(entries) == 1
        assert entries[0] == (".", RepoEntry(repo_name="my-repo"))
        assert warnings == []
```

Also add import at top of file:

```python
from gro.workspace import adopt_workspace_symlinks
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_basic_adoption -v`
Expected: FAIL with ImportError (function doesn't exist)

**Step 3: Write minimal implementation**

Add to `src/gro/workspace.py` after `scan_workspace_symlinks`:

```python
def adopt_workspace_symlinks(
    workspace: "Workspace",
    code_path: Path,
) -> tuple[list[tuple[str, "RepoEntry"]], list[str]]:
    """
    Scan workspace for symlinks pointing to code directory.

    Args:
        workspace: The workspace to scan.
        code_path: Path to the code directory.

    Returns:
        Tuple of:
        - List of (category_path, RepoEntry) to add to config
        - List of warning messages for skipped symlinks
    """
    from gro.models import RepoEntry

    entries: list[tuple[str, RepoEntry]] = []
    warnings: list[str] = []

    if not workspace.path.exists():
        return entries, warnings

    def scan_dir(dir_path: Path, category_prefix: str) -> None:
        """Recursively scan for symlinks."""
        for item in dir_path.iterdir():
            if item.is_symlink():
                cat_path = category_prefix if category_prefix else "."
                try:
                    target = item.resolve()
                    # Check if target is in code directory
                    try:
                        target.relative_to(code_path)
                        repo_name = target.name
                        symlink_name = item.name
                        if symlink_name != repo_name:
                            entry = RepoEntry(repo_name=repo_name, alias=symlink_name)
                        else:
                            entry = RepoEntry(repo_name=repo_name)
                        entries.append((cat_path, entry))
                    except ValueError:
                        # Target not in code directory
                        warnings.append(
                            f"Skipping {item.name} -> {target} (not in code directory)"
                        )
                except OSError:
                    # Broken symlink
                    warnings.append(f"Skipping {item.name} (broken symlink)")
            elif item.is_dir():
                new_prefix = (
                    f"{category_prefix}/{item.name}" if category_prefix else item.name
                )
                scan_dir(item, new_prefix)

    scan_dir(workspace.path, "")
    return entries, warnings
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_basic_adoption -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/gro/workspace.py tests/test_workspace.py
git commit -m "feat: add adopt_workspace_symlinks function"
```

---

## Task 2: Add Alias Detection Test

**Files:**

- Test: `tests/test_workspace.py`

**Step 1: Write failing test for alias detection**

Add to `TestAdoptWorkspaceSymlinks` class:

```python
    def test_alias_detection(self, tmp_path: Path) -> None:
        """Detects alias when symlink name differs from repo name."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "acme-code").mkdir()
        (code_path / "acme-code" / ".git").mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "git").symlink_to(code_path / "acme-code")

        workspace = Workspace(path=workspace_path)
        entries, warnings = adopt_workspace_symlinks(workspace, code_path)

        assert len(entries) == 1
        cat_path, entry = entries[0]
        assert cat_path == "."
        assert entry.repo_name == "acme-code"
        assert entry.alias == "git"
        assert entry.symlink_name == "git"
        assert warnings == []
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_alias_detection -v`
Expected: PASS (implementation already handles this)

**Step 3: Commit**

```bash
git add tests/test_workspace.py
git commit -m "test: add alias detection test for adopt_workspace_symlinks"
```

---

## Task 3: Add Nested Categories Test

**Files:**

- Test: `tests/test_workspace.py`

**Step 1: Write test for nested categories**

Add to `TestAdoptWorkspaceSymlinks` class:

```python
    def test_nested_categories(self, tmp_path: Path) -> None:
        """Derives category path from symlink location."""
        code_path = tmp_path / "code"
        code_path.mkdir()
        (code_path / "pyvmomi").mkdir()
        (code_path / "pyvmomi" / ".git").mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "vmware" / "vsphere").mkdir(parents=True)
        (workspace_path / "vmware" / "vsphere" / "pyvmomi").symlink_to(
            code_path / "pyvmomi"
        )

        workspace = Workspace(path=workspace_path)
        entries, warnings = adopt_workspace_symlinks(workspace, code_path)

        assert len(entries) == 1
        cat_path, entry = entries[0]
        assert cat_path == "vmware/vsphere"
        assert entry.repo_name == "pyvmomi"
        assert warnings == []
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_nested_categories -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_workspace.py
git commit -m "test: add nested categories test for adopt_workspace_symlinks"
```

---

## Task 4: Add Non-Code Symlink Warning Test

**Files:**

- Test: `tests/test_workspace.py`

**Step 1: Write test for non-code symlinks**

Add to `TestAdoptWorkspaceSymlinks` class:

```python
    def test_skips_non_code_symlinks(self, tmp_path: Path) -> None:
        """Warns and skips symlinks not pointing to code directory."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        external_path = tmp_path / "external"
        external_path.mkdir()
        (external_path / "tool").mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "tool").symlink_to(external_path / "tool")

        workspace = Workspace(path=workspace_path)
        entries, warnings = adopt_workspace_symlinks(workspace, code_path)

        assert entries == []
        assert len(warnings) == 1
        assert "not in code directory" in warnings[0]
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_skips_non_code_symlinks -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_workspace.py
git commit -m "test: add non-code symlink warning test"
```

---

## Task 5: Add Broken Symlink Warning Test

**Files:**

- Test: `tests/test_workspace.py`

**Step 1: Write test for broken symlinks**

Add to `TestAdoptWorkspaceSymlinks` class:

```python
    def test_skips_broken_symlinks(self, tmp_path: Path) -> None:
        """Warns and skips broken symlinks."""
        code_path = tmp_path / "code"
        code_path.mkdir()

        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        (workspace_path / "broken").symlink_to(tmp_path / "nonexistent")

        workspace = Workspace(path=workspace_path)
        entries, warnings = adopt_workspace_symlinks(workspace, code_path)

        assert entries == []
        assert len(warnings) == 1
        assert "broken symlink" in warnings[0]
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_workspace.py::TestAdoptWorkspaceSymlinks::test_skips_broken_symlinks -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_workspace.py
git commit -m "test: add broken symlink warning test"
```

---

## Task 6: Integrate into `init --scan`

**Files:**

- Modify: `src/gro/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write failing test for init adopting symlinks**

Add to `tests/test_cli.py` in the `TestInit` class:

```python
    def test_scan_adopts_existing_symlinks(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """--scan adopts existing workspace symlinks."""
        code_path = test_env["code_path"]
        workspace_path = test_env["workspace_path"]
        config_path = test_env["config_path"]

        # Create repo in code directory
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        # Create existing symlink in workspace
        (workspace_path / "tools").mkdir()
        (workspace_path / "tools" / "my-repo").symlink_to(code_path / "my-repo")

        result = runner.invoke(
            main, ["--config", str(config_path), "init", "--scan", "--non-interactive"]
        )

        assert result.exit_code == 0
        assert "Adopting existing symlinks" in result.output

        # Verify config has the repo in correct category
        config = load_config(config_path)
        workspace = config.workspaces["workspace"]
        assert "tools" in workspace.categories
        assert "my-repo" in workspace.categories["tools"].repo_names
```

Also add import if not present:

```python
from gro.config import load_config
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::TestInit::test_scan_adopts_existing_symlinks -v`
Expected: FAIL (no "Adopting existing symlinks" output)

**Step 3: Modify init command to adopt symlinks**

In `src/gro/cli.py`, add import at top:

```python
from gro.workspace import adopt_workspace_symlinks
```

In the `init` function, after creating workspace directories (around line 290), before the `if scan and config.code_path.exists():` block, add:

```python
    # Adopt existing workspace symlinks if --scan
    if scan:
        for ws_name, workspace in config.workspaces.items():
            if workspace.path.exists():
                entries, adopt_warnings = adopt_workspace_symlinks(
                    workspace, config.code_path
                )
                if entries:
                    console.print(f"\n[bold]Adopting existing symlinks from {ws_name}:[/bold]")
                    for cat_path, entry in entries:
                        category = workspace.get_or_create_category(cat_path)
                        if entry.repo_name not in category.repo_names:
                            category.entries.append(entry)
                            display = format_symlink_path(ws_name, cat_path, entry.symlink_name)
                            if entry.alias:
                                console.print(
                                    f"  [green]+[/green] {display} -> {entry.repo_name}"
                                )
                            else:
                                console.print(f"  [green]+[/green] {display}")
                for warning in adopt_warnings:
                    console.print(f"  [yellow]![/yellow] {warning}")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::TestInit::test_scan_adopts_existing_symlinks -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `make test`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/gro/cli.py tests/test_cli.py
git commit -m "feat: init --scan adopts existing workspace symlinks"
```

---

## Task 7: Test Init Alias Adoption

**Files:**

- Test: `tests/test_cli.py`

**Step 1: Write test for init adopting aliases**

Add to `TestInit` class:

```python
    def test_scan_adopts_symlinks_with_aliases(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """--scan preserves aliases when adopting symlinks."""
        code_path = test_env["code_path"]
        workspace_path = test_env["workspace_path"]
        config_path = test_env["config_path"]

        # Create repo with different name than symlink
        (code_path / "acme-code" / ".git").mkdir(parents=True)

        # Create aliased symlink
        (workspace_path / "git").symlink_to(code_path / "acme-code")

        result = runner.invoke(
            main, ["--config", str(config_path), "init", "--scan", "--non-interactive"]
        )

        assert result.exit_code == 0

        config = load_config(config_path)
        workspace = config.workspaces["workspace"]
        assert "." in workspace.categories
        entries = workspace.categories["."].entries
        assert len(entries) == 1
        assert entries[0].repo_name == "acme-code"
        assert entries[0].alias == "git"
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::TestInit::test_scan_adopts_symlinks_with_aliases -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: verify init --scan preserves symlink aliases"
```

---

## Task 8: Integrate into `sync`

**Files:**

- Modify: `src/gro/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write failing test for sync adopting orphaned symlinks**

Add new test class to `tests/test_cli.py`:

```python
class TestSyncAdoptSymlinks:
    """Tests for sync command adopting orphaned symlinks."""

    def test_adopts_orphaned_symlinks(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """sync adopts orphaned workspace symlinks."""
        code_path = test_env["code_path"]
        workspace_path = test_env["workspace_path"]
        config_path = test_env["config_path"]

        # Create repo in code directory
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        # Create initial config without the repo
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(f"""
code: {code_path}
workspaces:
  - {workspace_path}
""")

        # Create orphaned symlink in workspace
        (workspace_path / "tools").mkdir()
        (workspace_path / "tools" / "my-repo").symlink_to(code_path / "my-repo")

        result = runner.invoke(
            main, ["--config", str(config_path), "sync", "--non-interactive"]
        )

        assert result.exit_code == 0
        assert "Adopting orphaned symlinks" in result.output

        config = load_config(config_path)
        workspace = config.workspaces["workspace"]
        assert "tools" in workspace.categories
        assert "my-repo" in workspace.categories["tools"].repo_names
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::TestSyncAdoptSymlinks::test_adopts_orphaned_symlinks -v`
Expected: FAIL (no "Adopting orphaned symlinks" output)

**Step 3: Modify sync command**

In `src/gro/cli.py`, in the `sync` function, after calculating `uncategorized` repos (around line 663), add:

```python
    # Also adopt orphaned workspace symlinks
    adopted_count = 0
    for ws_name, workspace in config.workspaces.items():
        if workspace.path.exists():
            entries, adopt_warnings = adopt_workspace_symlinks(workspace, config.code_path)
            # Filter to only entries not already in config
            orphaned_entries = [
                (cat_path, entry)
                for cat_path, entry in entries
                if entry.repo_name not in repos_in_config
            ]
            if orphaned_entries:
                console.print(f"\n[bold]Adopting orphaned symlinks from {ws_name}:[/bold]")
                for cat_path, entry in orphaned_entries:
                    category = workspace.get_or_create_category(cat_path)
                    if entry.repo_name not in category.repo_names:
                        category.entries.append(entry)
                        repos_in_config.add(entry.repo_name)
                        display = format_symlink_path(ws_name, cat_path, entry.symlink_name)
                        if entry.alias:
                            console.print(
                                f"  [green]+[/green] {display} -> {entry.repo_name}"
                            )
                        else:
                            console.print(f"  [green]+[/green] {display}")
                        adopted_count += 1
            for warning in adopt_warnings:
                console.print(f"  [yellow]![/yellow] {warning}")

    # Update uncategorized after adoption
    uncategorized = repos_in_code - repos_in_config
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::TestSyncAdoptSymlinks::test_adopts_orphaned_symlinks -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `make test`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/gro/cli.py tests/test_cli.py
git commit -m "feat: sync adopts orphaned workspace symlinks"
```

---

## Task 9: Test Sync Skips Already-Configured Repos

**Files:**

- Test: `tests/test_cli.py`

**Step 1: Write test for sync skipping configured repos**

Add to `TestSyncAdoptSymlinks` class:

```python
    def test_skips_already_configured_repos(
        self, runner: CliRunner, test_env: dict[str, Path]
    ) -> None:
        """sync doesn't duplicate repos already in config."""
        code_path = test_env["code_path"]
        workspace_path = test_env["workspace_path"]
        config_path = test_env["config_path"]

        # Create repo in code directory
        (code_path / "my-repo" / ".git").mkdir(parents=True)

        # Create config with the repo already configured
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(f"""
code: {code_path}
workspaces:
  - {workspace_path}
workspace:
  .:
    - my-repo
""")

        # Create symlink (matching config)
        (workspace_path / "my-repo").symlink_to(code_path / "my-repo")

        result = runner.invoke(
            main, ["--config", str(config_path), "sync", "--non-interactive"]
        )

        assert result.exit_code == 0
        assert "All repos are categorized" in result.output
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::TestSyncAdoptSymlinks::test_skips_already_configured_repos -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: verify sync skips already-configured repos"
```

---

## Task 10: Final Validation and Cleanup

**Step 1: Run full test suite**

Run: `make check`
Expected: All checks pass (lint, typecheck, tests)

**Step 2: Fix any lint/type issues if needed**

**Step 3: Final commit if any fixes**

```bash
git add -u
git commit -m "chore: fix lint/type issues"
```

**Step 4: Verify feature works manually**

```bash
# Create test scenario
mkdir -p /tmp/gro-test/code/test-repo/.git
mkdir -p /tmp/gro-test/workspace/tools
ln -s /tmp/gro-test/code/test-repo /tmp/gro-test/workspace/tools/test-repo

# Test init --scan
uv run gro --config /tmp/gro-test/config.yaml init \
    --code /tmp/gro-test/code \
    --workspace /tmp/gro-test/workspace \
    --scan --non-interactive

# Verify config
cat /tmp/gro-test/config.yaml

# Cleanup
rm -rf /tmp/gro-test
```
