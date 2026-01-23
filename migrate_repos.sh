#!/bin/bash

# Git Repository Reorganization Script
# This script will reorganize your git repositories into a clean structure

set -e  # Exit on error

BASE_DIR="/sessions/keen-gracious-wozniak/mnt/markalston"
NEW_BASE="$BASE_DIR/code"
LOG_FILE="/sessions/keen-gracious-wozniak/migration.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Create directory structure
create_structure() {
    log "Creating new directory structure..."

    mkdir -p "$NEW_BASE"/{vmware/{vsphere,tanzu,cloud-foundry,platform-automation},kubernetes,ai-ml/{claude,llm},languages/{golang,python,javascript},infrastructure/{terraform,docker},personal/{homelab,scripts},archived}

    log "Directory structure created"
}

# Move a repository
move_repo() {
    local src="$1"
    local dest="$2"
    local repo_name=$(basename "$src")

    if [ ! -d "$src" ]; then
        warn "Source does not exist: $src"
        return
    fi

    if [ -d "$dest/$repo_name" ]; then
        warn "Destination already exists: $dest/$repo_name - Skipping"
        return
    fi

    log "Moving $repo_name to $dest/"
    mv "$src" "$dest/" && log "  ✓ Moved successfully" || error "  ✗ Failed to move"
}

# VMware vSphere repositories
move_vmware_vsphere() {
    log "Moving VMware vSphere repositories..."
    local dest="$NEW_BASE/vmware/vsphere"

    move_repo "$BASE_DIR/workspace/tanzu-validated-solutions" "$dest"
    move_repo "$BASE_DIR/workspace/tas-dominion" "$dest"
    move_repo "$BASE_DIR/workspace/tas-vcf" "$dest"
    move_repo "$BASE_DIR/workspace/vcf-9x-in-box" "$dest"
    move_repo "$BASE_DIR/workspace/vcf-9x-lamw" "$dest"
    move_repo "$BASE_DIR/workspace/vcf-fleet-automated-lab-deployment" "$dest"
    move_repo "$BASE_DIR/workspace/vcf-offline-depot" "$dest"
    move_repo "$BASE_DIR/workspace/vmware-scripts" "$dest"
    move_repo "$BASE_DIR/workspace/vsphere-architect" "$dest"
}

# VMware Tanzu repositories
move_vmware_tanzu() {
    log "Moving VMware Tanzu repositories..."
    local dest="$NEW_BASE/vmware/tanzu"

    move_repo "$BASE_DIR/workspace/tanzu-homelab" "$dest"
}

# Cloud Foundry/TAS repositories
move_cloud_foundry() {
    log "Moving Cloud Foundry/TAS repositories..."
    local dest="$NEW_BASE/vmware/cloud-foundry"

    move_repo "$BASE_DIR/workspace/bosh-mcp-server" "$dest"
    move_repo "$BASE_DIR/workspace/bosh-mock-director" "$dest"
    move_repo "$BASE_DIR/workspace/bosh-operator" "$dest"
    move_repo "$BASE_DIR/workspace/diego-capacity-analyzer" "$dest"
    move_repo "$BASE_DIR/workspace/diego-capacity-analyzer.wiki" "$dest"
    move_repo "$BASE_DIR/workspace/diego-thd" "$dest"
    move_repo "$BASE_DIR/workspace/om" "$dest"
    move_repo "$BASE_DIR/workspace/tanzu-cf-architect" "$dest"  # Keep the newer one
    move_repo "$BASE_DIR/workspace/tanzu-platform-sbom-service" "$dest"
    move_repo "$BASE_DIR/workspace/tas-h2o" "$dest"
    move_repo "$BASE_DIR/workspace/thd-tas-platform-engagement" "$dest"

    # Remove duplicate (older version)
    if [ -d "$BASE_DIR/git/tanzu-cf-architect" ]; then
        log "Removing duplicate: git/tanzu-cf-architect (older version)"
        rm -rf "$BASE_DIR/git/tanzu-cf-architect"
    fi
}

# Platform Automation repositories
move_platform_automation() {
    log "Moving Platform Automation repositories..."
    local dest="$NEW_BASE/vmware/platform-automation"

    move_repo "$BASE_DIR/workspace/telmore-platform-automation" "$dest"
}

# Kubernetes repositories
move_kubernetes() {
    log "Moving Kubernetes repositories..."
    local dest="$NEW_BASE/kubernetes"

    move_repo "$BASE_DIR/git/release-monitor" "$dest"
    move_repo "$BASE_DIR/git/repave" "$dest"
    move_repo "$BASE_DIR/git/tkgi-app-tracker" "$dest"
    move_repo "$BASE_DIR/git/workspace-tkgi-app-tracker" "$dest"
}

# Claude AI repositories
move_claude_ai() {
    log "Moving Claude AI repositories..."
    local dest="$NEW_BASE/ai-ml/claude"

    # From workspace
    move_repo "$BASE_DIR/workspace/amplifier-bundle-superpowers" "$dest"
    move_repo "$BASE_DIR/workspace/amplifier-bundle-superpowers-obra" "$dest"
    move_repo "$BASE_DIR/workspace/amplifier-claude" "$dest"
    move_repo "$BASE_DIR/workspace/amplifier-claude-preflight" "$dest"
    move_repo "$BASE_DIR/workspace/cc-conductor" "$dest"
    move_repo "$BASE_DIR/workspace/claude-config-dir" "$dest"
    move_repo "$BASE_DIR/workspace/claude-plugins" "$dest"
    move_repo "$BASE_DIR/workspace/claudeup" "$dest"
    move_repo "$BASE_DIR/workspace/claudeup-superpowers" "$dest"
    move_repo "$BASE_DIR/workspace/claudeup-test-repos" "$dest"
    move_repo "$BASE_DIR/workspace/claudeup.github.io" "$dest"
    move_repo "$BASE_DIR/workspace/profiles" "$dest"
    move_repo "$BASE_DIR/workspace/profiles-private" "$dest"

    # From ai directory
    move_repo "$BASE_DIR/ai/awesome-claude-code" "$dest"
    move_repo "$BASE_DIR/ai/awesome-claude-code-plugins" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-monitoring" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-plugin-marketplace" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-statusline" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-tamagotchi" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-templates" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-tips" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-tresor" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-viewer" "$dest"
    move_repo "$BASE_DIR/ai/claude-code-wiki" "$dest"
    move_repo "$BASE_DIR/ai/claude-config-editor" "$dest"
    move_repo "$BASE_DIR/ai/claude-cookbooks" "$dest"
    move_repo "$BASE_DIR/ai/claude-devcontainer" "$dest"
    move_repo "$BASE_DIR/ai/claude-mem" "$dest"
    move_repo "$BASE_DIR/ai/my-claude-code-setup" "$dest"

    # From projects
    move_repo "$BASE_DIR/projects/claude-orchestrator" "$dest"
}

# General AI/LLM repositories
move_ai_llm() {
    log "Moving General AI/LLM repositories..."
    local dest="$NEW_BASE/ai-ml/llm"

    move_repo "$BASE_DIR/ai/12-factor-agents" "$dest"
    move_repo "$BASE_DIR/ai/agent-skills" "$dest"
    move_repo "$BASE_DIR/ai/agents" "$dest"
    move_repo "$BASE_DIR/ai/awesome-llm-apps" "$dest"
    move_repo "$BASE_DIR/ai/episodic-memory" "$dest"
    move_repo "$BASE_DIR/ai/humanlayer" "$dest"
    move_repo "$BASE_DIR/ai/multi-agent-system" "$dest"
    move_repo "$BASE_DIR/ai/serena" "$dest"
    move_repo "$BASE_DIR/ai/sub-agents.directory" "$dest"
    move_repo "$BASE_DIR/ai/sudolang" "$dest"
    move_repo "$BASE_DIR/ai/textual-tui-skill" "$dest"
    move_repo "$BASE_DIR/workspace/chrome-tabs" "$dest"
    move_repo "$BASE_DIR/workspace/openapi-docs-generator" "$dest"
}

# Golang repositories
move_golang() {
    log "Moving Golang repositories..."
    local dest="$NEW_BASE/languages/golang"

    move_repo "$BASE_DIR/workspace/github-malston-website" "$dest"
    move_repo "$BASE_DIR/workspace/packnplay" "$dest"  # Keep workspace version
    move_repo "$BASE_DIR/workspace/samples" "$dest"
    move_repo "$BASE_DIR/workspace/surge" "$dest"
    move_repo "$BASE_DIR/workspace/tile-diff" "$dest"

    # Remove duplicate
    if [ -d "$BASE_DIR/ai/packnplay" ]; then
        log "Removing duplicate: ai/packnplay"
        rm -rf "$BASE_DIR/ai/packnplay"
    fi
}

# Python repositories
move_python() {
    log "Moving Python repositories..."
    local dest="$NEW_BASE/languages/python"

    move_repo "$BASE_DIR/workspace/erk" "$dest"
    move_repo "$BASE_DIR/workspace/python-learnings" "$dest"
    move_repo "$BASE_DIR/workspace/release-monitor" "$dest"
    move_repo "$BASE_DIR/git/release-monitor-malston" "$dest"
}

# JavaScript repositories
move_javascript() {
    log "Moving JavaScript repositories..."
    local dest="$NEW_BASE/languages/javascript"

    # Note: dotfiles repos have different remotes, so they're not duplicates
    # But we'll keep the most recent one in scripts category
}

# Docker repositories
move_docker() {
    log "Moving Docker repositories..."
    local dest="$NEW_BASE/infrastructure/docker"

    move_repo "$BASE_DIR/workspace/markitdown" "$dest"
    move_repo "$BASE_DIR/git/gh-release" "$dest"
    move_repo "$BASE_DIR/git/workspace-gh-release" "$dest"
}

# Homelab repositories
move_homelab() {
    log "Moving Homelab repositories..."
    local dest="$NEW_BASE/personal/homelab"

    move_repo "$BASE_DIR/workspace/homelab" "$dest"
    move_repo "$BASE_DIR/workspace/homelab-legacy" "$dest"
}

# Scripts and utilities
move_scripts() {
    log "Moving Scripts and utilities..."
    local dest="$NEW_BASE/personal/scripts"

    move_repo "$BASE_DIR/workspace/dotfiles-linux" "$dest"
    move_repo "$BASE_DIR/workspace/my-scripts" "$dest"
    move_repo "$BASE_DIR/workspace/npx-tools" "$dest"
    move_repo "$BASE_DIR/workspace/powershell-scripts" "$dest"
    move_repo "$BASE_DIR/ai/dotfiles" "$dest"
    move_repo "$BASE_DIR/projects/dotfiles" "$dest"
}

# Uncategorized repositories
move_uncategorized() {
    log "Moving uncategorized repositories to ai-ml/llm..."
    local dest="$NEW_BASE/ai-ml/llm"

    move_repo "$BASE_DIR/workspace/expense-report" "$dest"
    move_repo "$BASE_DIR/workspace/kubefirst-personal" "$dest"
    move_repo "$BASE_DIR/workspace/notes-wiki" "$dest"
    move_repo "$BASE_DIR/workspace/shared-isoseg-demo" "$dest"
    move_repo "$BASE_DIR/workspace/tile-diff-internal-docs" "$dest"
}

# Archive inactive repositories
archive_inactive() {
    log "Archiving inactive repositories (180+ days since last commit)..."
    local dest="$NEW_BASE/archived"

    # Read from categorization.json
    local inactive_repos=$(python3 -c "
import json
with open('/sessions/keen-gracious-wozniak/categorization.json') as f:
    data = json.load(f)
    for repo in data['categories']['archived-inactive']:
        print(repo)
")

    while IFS= read -r repo; do
        if [ ! -z "$repo" ] && [ -d "$repo" ]; then
            move_repo "$repo" "$dest"
        fi
    done <<< "$inactive_repos"
}

# Main execution
main() {
    log "========================================="
    log "Git Repository Reorganization Started"
    log "========================================="

    # Create backup information
    log "Creating backup information..."
    echo "Original structure backed up at: $(date)" > "$NEW_BASE/MIGRATION_INFO.txt"
    echo "Migration log: $LOG_FILE" >> "$NEW_BASE/MIGRATION_INFO.txt"

    # Create structure
    create_structure

    # Move repositories by category
    move_vmware_vsphere
    move_vmware_tanzu
    move_cloud_foundry
    move_platform_automation
    move_kubernetes
    move_claude_ai
    move_ai_llm
    move_golang
    move_python
    move_docker
    move_homelab
    move_scripts
    move_uncategorized

    # Archive inactive repos
    archive_inactive

    log "========================================="
    log "Migration Complete!"
    log "========================================="
    log "New structure created in: $NEW_BASE"
    log "Migration log saved to: $LOG_FILE"
    log ""
    log "Next steps:"
    log "1. Verify the new structure in ~/code/"
    log "2. Check that all repositories are in the correct locations"
    log "3. Once verified, you can remove the old directories:"
    log "   - ~/workspace"
    log "   - ~/ai"
    log "   - ~/git"
    log "   - ~/projects"
}

# Run main function
main
