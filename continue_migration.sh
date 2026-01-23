#!/bin/bash

# Continue Git Repository Reorganization Script

BASE_DIR="/sessions/keen-gracious-wozniak/mnt/markalston"
NEW_BASE="$BASE_DIR/code"
LOG_FILE="/sessions/keen-gracious-wozniak/migration.log"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

move_repo() {
    local src="$1"
    local dest="$2"
    local repo_name=$(basename "$src")

    if [ ! -d "$src" ]; then
        return
    fi

    if [ -d "$dest/$repo_name" ]; then
        warn "Already exists: $dest/$repo_name - Skipping"
        return
    fi

    log "Moving $repo_name to $dest/"
    if mv "$src" "$dest/" 2>/dev/null; then
        log "  ✓ Moved successfully"
    else
        warn "  ✗ Failed to move (may have permission issues)"
    fi
}

log "Continuing migration..."

# Platform Automation
log "Moving Platform Automation repositories..."
move_repo "$BASE_DIR/workspace/telmore-platform-automation" "$NEW_BASE/vmware/platform-automation"

# Kubernetes
log "Moving Kubernetes repositories..."
move_repo "$BASE_DIR/git/release-monitor" "$NEW_BASE/kubernetes"
move_repo "$BASE_DIR/git/repave" "$NEW_BASE/kubernetes"
move_repo "$BASE_DIR/git/tkgi-app-tracker" "$NEW_BASE/kubernetes"
move_repo "$BASE_DIR/git/workspace-tkgi-app-tracker" "$NEW_BASE/kubernetes"

# Claude AI - workspace
log "Moving Claude AI repositories from workspace..."
move_repo "$BASE_DIR/workspace/amplifier-bundle-superpowers" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/amplifier-bundle-superpowers-obra" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/amplifier-claude" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/amplifier-claude-preflight" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/cc-conductor" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claude-config-dir" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claude-plugins" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claudeup" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claudeup-superpowers" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claudeup-test-repos" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/claudeup.github.io" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/profiles" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/workspace/profiles-private" "$NEW_BASE/ai-ml/claude"

# Claude AI - ai directory
log "Moving Claude AI repositories from ai..."
move_repo "$BASE_DIR/ai/awesome-claude-code" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/awesome-claude-code-plugins" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-monitoring" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-plugin-marketplace" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-statusline" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-tamagotchi" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-templates" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-tips" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-tresor" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-viewer" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-code-wiki" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-config-editor" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-cookbooks" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-devcontainer" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/claude-mem" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/ai/my-claude-code-setup" "$NEW_BASE/ai-ml/claude"
move_repo "$BASE_DIR/projects/claude-orchestrator" "$NEW_BASE/ai-ml/claude"

# General AI/LLM
log "Moving General AI/LLM repositories..."
move_repo "$BASE_DIR/ai/12-factor-agents" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/agent-skills" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/agents" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/awesome-llm-apps" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/episodic-memory" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/humanlayer" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/multi-agent-system" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/serena" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/sub-agents.directory" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/sudolang" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/ai/textual-tui-skill" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/chrome-tabs" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/openapi-docs-generator" "$NEW_BASE/ai-ml/llm"

# Golang
log "Moving Golang repositories..."
move_repo "$BASE_DIR/workspace/github-malston-website" "$NEW_BASE/languages/golang"
move_repo "$BASE_DIR/workspace/packnplay" "$NEW_BASE/languages/golang"
move_repo "$BASE_DIR/workspace/samples" "$NEW_BASE/languages/golang"
move_repo "$BASE_DIR/workspace/surge" "$NEW_BASE/languages/golang"
move_repo "$BASE_DIR/workspace/tile-diff" "$NEW_BASE/languages/golang"

# Python
log "Moving Python repositories..."
move_repo "$BASE_DIR/workspace/erk" "$NEW_BASE/languages/python"
move_repo "$BASE_DIR/workspace/python-learnings" "$NEW_BASE/languages/python"
move_repo "$BASE_DIR/workspace/release-monitor" "$NEW_BASE/languages/python"
move_repo "$BASE_DIR/git/release-monitor-malston" "$NEW_BASE/languages/python"

# Docker
log "Moving Docker repositories..."
move_repo "$BASE_DIR/workspace/markitdown" "$NEW_BASE/infrastructure/docker"
move_repo "$BASE_DIR/git/gh-release" "$NEW_BASE/infrastructure/docker"
move_repo "$BASE_DIR/git/workspace-gh-release" "$NEW_BASE/infrastructure/docker"

# Homelab
log "Moving Homelab repositories..."
move_repo "$BASE_DIR/workspace/homelab" "$NEW_BASE/personal/homelab"
move_repo "$BASE_DIR/workspace/homelab-legacy" "$NEW_BASE/personal/homelab"

# Scripts and utilities
log "Moving Scripts and utilities..."
move_repo "$BASE_DIR/workspace/dotfiles-linux" "$NEW_BASE/personal/scripts"
move_repo "$BASE_DIR/workspace/my-scripts" "$NEW_BASE/personal/scripts"
move_repo "$BASE_DIR/workspace/npx-tools" "$NEW_BASE/personal/scripts"
move_repo "$BASE_DIR/workspace/powershell-scripts" "$NEW_BASE/personal/scripts"
move_repo "$BASE_DIR/ai/dotfiles" "$NEW_BASE/personal/scripts"
move_repo "$BASE_DIR/projects/dotfiles" "$NEW_BASE/personal/scripts"

# Uncategorized
log "Moving uncategorized repositories..."
move_repo "$BASE_DIR/workspace/expense-report" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/kubefirst-personal" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/notes-wiki" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/shared-isoseg-demo" "$NEW_BASE/ai-ml/llm"
move_repo "$BASE_DIR/workspace/tile-diff-internal-docs" "$NEW_BASE/ai-ml/llm"

# Archive inactive repositories
log "Archiving inactive repositories..."
python3 -c "
import json
with open('/sessions/keen-gracious-wozniak/categorization.json') as f:
    data = json.load(f)
    for repo in data['categories']['archived-inactive']:
        print(repo)
" | while IFS= read -r repo; do
    if [ ! -z "$repo" ] && [ -d "$repo" ]; then
        move_repo "$repo" "$NEW_BASE/archived"
    fi
done

# Handle duplicates - try to remove but don't fail if permission denied
log "Attempting to clean up duplicates..."
if [ -d "$BASE_DIR/ai/packnplay" ]; then
    log "Removing duplicate: ai/packnplay"
    rm -rf "$BASE_DIR/ai/packnplay" 2>/dev/null || warn "Could not remove ai/packnplay (permission denied - you can remove manually)"
fi

if [ -d "$BASE_DIR/git/tanzu-cf-architect" ]; then
    log "Removing duplicate: git/tanzu-cf-architect"
    rm -rf "$BASE_DIR/git/tanzu-cf-architect" 2>/dev/null || warn "Could not remove git/tanzu-cf-architect (permission denied - you can remove manually)"
fi

log "========================================="
log "Migration Complete!"
log "========================================="

# Generate summary
TOTAL_MIGRATED=$(find "$NEW_BASE" -type d -name ".git" | wc -l)
log "Total repositories in new structure: $TOTAL_MIGRATED"
log "New structure: $NEW_BASE"
log "Migration log: $LOG_FILE"
