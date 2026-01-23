#!/bin/bash

# Script to analyze git repositories
OUTPUT_FILE="/sessions/keen-gracious-wozniak/repo_analysis.csv"

echo "repo_path,repo_name,last_commit_date,days_since_commit,primary_language,remote_url,directory" > "$OUTPUT_FILE"

analyze_repo() {
    local repo_path="$1"
    local parent_dir="$2"
    
    cd "$repo_path" 2>/dev/null || return
    
    # Get repo name
    repo_name=$(basename "$repo_path")
    
    # Get last commit date
    last_commit=$(git log -1 --format=%ci 2>/dev/null | cut -d' ' -f1)
    if [ -z "$last_commit" ]; then
        last_commit="no-commits"
        days_since=999999
    else
        days_since=$(( ( $(date +%s) - $(date -d "$last_commit" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$last_commit" +%s) ) / 86400 ))
    fi
    
    # Get primary language (basic heuristic)
    if [ -f "go.mod" ] || [ -f "main.go" ]; then
        lang="go"
    elif [ -f "package.json" ]; then
        lang="javascript"
    elif [ -f "requirements.txt" ] || [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
        lang="python"
    elif [ -f "Gemfile" ]; then
        lang="ruby"
    elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
        lang="java"
    elif [ -d "terraform" ] || [ -f "main.tf" ]; then
        lang="terraform"
    elif [ -f "Dockerfile" ]; then
        lang="docker"
    else
        lang="unknown"
    fi
    
    # Get remote URL
    remote_url=$(git remote get-url origin 2>/dev/null || echo "no-remote")
    
    echo "\"$repo_path\",\"$repo_name\",\"$last_commit\",$days_since,\"$lang\",\"$remote_url\",\"$parent_dir\"" >> "$OUTPUT_FILE"
}

# Analyze all repos
for dir in workspace ai git projects; do
    repo_base="/sessions/keen-gracious-wozniak/mnt/markalston/$dir"
    if [ -d "$repo_base" ]; then
        find "$repo_base" -maxdepth 2 -name ".git" -type d 2>/dev/null | while read git_dir; do
            repo_path=$(dirname "$git_dir")
            analyze_repo "$repo_path" "$dir"
        done
    fi
done

echo "Analysis complete. Results in $OUTPUT_FILE"
