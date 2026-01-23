# Git Repository Reorganization Plan

## Summary
- **Total Repositories**: 153
- **Duplicate Repository Names**: 4
- **Inactive Repositories (180+ days)**: 57

## Duplicate Repositories

You have 4 repository names that appear in multiple locations:

### 1. dotfiles (2 copies)
- `projects/dotfiles` - Last commit: 2026-01-03 (20 days ago) - https://github.com/fredrikaverpil/dotfiles.git
- `ai/dotfiles` - Last commit: 2025-10-25 (90 days ago) - https://github.com/obra/dotfiles.git
**Note**: These are actually different repositories (different remotes), not duplicates

### 2. packnplay (2 copies)
- `workspace/packnplay` - Last commit: 2025-11-29 (55 days ago) - https://github.com/obra/packnplay.git
- `ai/packnplay` - Last commit: 2025-11-29 (55 days ago) - https://github.com/obra/packnplay.git
**Note**: Same repository, same remote - TRUE DUPLICATE

### 3. release-monitor (2 copies)
- `git/release-monitor` - Last commit: 2025-09-29 (116 days ago) - git@github3.wellsfargo.com:Utilities-tkgieng/release-monitor.git
- `workspace/release-monitor` - Last commit: 2025-09-17 (128 days ago) - https://github.com/malston/release-monitor.git
**Note**: Different remotes (Wells Fargo vs personal), not true duplicates

### 4. tanzu-cf-architect (2 copies)
- `workspace/tanzu-cf-architect` - Last commit: 2026-01-08 (15 days ago) - https://github.com/malston/tanzu-cf-architect-claude-plugin.git
- `git/tanzu-cf-architect` - Last commit: 2025-12-19 (35 days ago) - https://github.com/malston/tanzu-cf-architect-claude-plugin.git
**Note**: Same repository - TRUE DUPLICATE (workspace version is newer)

## Proposed Directory Structure

```
~/code/
├── vmware/
│   ├── vsphere/          # vSphere, VCF, ESXi projects (9 repos)
│   ├── tanzu/            # Tanzu-specific projects (1 repo)
│   ├── cloud-foundry/    # TAS, Diego, BOSH projects (12 repos)
│   └── platform-automation/  # Platform automation (1 repo)
├── kubernetes/           # K8s, TKGI projects (4 repos)
├── ai-ml/
│   ├── claude/          # Claude-related projects (30 repos)
│   ├── llm/             # General LLM/AI projects (13 repos)
├── languages/
│   ├── golang/          # Go projects (6 repos)
│   ├── python/          # Python projects (5 repos)
│   ├── javascript/      # JavaScript/Node projects (4 repos)
├── infrastructure/
│   ├── terraform/       # Terraform projects (0 repos currently in terraform cat)
│   ├── docker/          # Docker projects (3 repos)
├── personal/
│   ├── homelab/         # Homelab projects (2 repos)
│   ├── scripts/         # Dotfiles, scripts, utilities (6 repos)
└── archived/            # Inactive repos (57 repos)
```

## Actions to Take

### 1. Handle Duplicates
- **packnplay**: Keep `workspace/packnplay`, remove `ai/packnplay` (identical)
- **tanzu-cf-architect**: Keep `workspace/tanzu-cf-architect` (newer), remove `git/tanzu-cf-architect`

### 2. Archive Inactive Repositories (57 repos)
Move all repositories with no commits in 180+ days to `~/code/archived/`

### 3. Reorganize Active Repositories (94 repos)
Move active repositories from ~/workspace, ~/ai, ~/git, ~/projects to the new organized structure in ~/code/

## Migration Commands

A script will be generated to:
1. Create the new directory structure in `~/code/`
2. Move repositories to their appropriate categories
3. Archive inactive repositories
4. Clean up duplicate repositories
5. Generate a migration log for reference

## Post-Migration

After migration, you'll have:
- A clean, categorized structure in `~/code/`
- All inactive repositories in `~/code/archived/` for future reference
- Duplicates removed
- Original directories (~/workspace, ~/ai, ~/git, ~/projects) can be removed after verification
