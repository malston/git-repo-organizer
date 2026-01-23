#!/usr/bin/env python3

import csv
from collections import defaultdict
from datetime import datetime, timedelta
import json

# Read the CSV data
repos = []
with open('/sessions/keen-gracious-wozniak/repo_analysis.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        repos.append(row)

# Find duplicates by repo name
duplicates = defaultdict(list)
for repo in repos:
    duplicates[repo['repo_name']].append(repo)

# Filter to only actual duplicates
actual_duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}

# Categorize repositories
categories = {
    'vmware-vsphere': [],
    'cloud-foundry-tas': [],
    'kubernetes': [],
    'claude-ai': [],
    'platform-automation': [],
    'golang': [],
    'python': [],
    'javascript': [],
    'terraform-infrastructure': [],
    'docker-containers': [],
    'vmware-tanzu': [],
    'scripts-utilities': [],
    'homelab-personal': [],
    'archived-inactive': [],
    'uncategorized': []
}

# Categorization logic
for repo in repos:
    name = repo['repo_name'].lower()
    remote = repo['remote_url'].lower()
    lang = repo['primary_language']
    days_since = int(repo['days_since_commit'])

    # Mark as inactive if over 180 days
    if days_since >= 180:
        categories['archived-inactive'].append(repo)
        continue

    # VMware/vSphere related
    if any(x in name or x in remote for x in ['vsphere', 'vcf', 'vmware', 'esxi', 'hcx']):
        categories['vmware-vsphere'].append(repo)
    # Cloud Foundry/TAS
    elif any(x in name or x in remote for x in ['tas-', 'diego', 'bosh', 'cf-', 'cloud-foundry', 'pivotal', 'mapbu', 'pcf']):
        categories['cloud-foundry-tas'].append(repo)
    # Kubernetes
    elif any(x in name or x in remote for x in ['k8s', 'kubernetes', 'tkgi', 'cks-', 'kubectl', 'istio', 'gatekeeper']):
        categories['kubernetes'].append(repo)
    # Claude AI
    elif any(x in name or x in remote for x in ['claude', 'anthropic', 'amplifier']):
        categories['claude-ai'].append(repo)
    # Platform Automation
    elif 'platform-automation' in name or 'platform-automation' in remote:
        categories['platform-automation'].append(repo)
    # Tanzu
    elif 'tanzu' in name or 'tanzu' in remote:
        categories['vmware-tanzu'].append(repo)
    # By language
    elif lang == 'go':
        categories['golang'].append(repo)
    elif lang == 'python':
        categories['python'].append(repo)
    elif lang == 'javascript':
        categories['javascript'].append(repo)
    elif lang == 'terraform':
        categories['terraform-infrastructure'].append(repo)
    elif lang == 'docker':
        categories['docker-containers'].append(repo)
    # Scripts and utilities
    elif any(x in name for x in ['script', 'tool', 'util', 'dotfiles', 'setup', 'config']):
        categories['scripts-utilities'].append(repo)
    # Homelab
    elif 'homelab' in name or 'homelab' in remote:
        categories['homelab-personal'].append(repo)
    else:
        categories['uncategorized'].append(repo)

# Generate reports
print("=" * 80)
print("DUPLICATE REPOSITORIES REPORT")
print("=" * 80)
print()

if actual_duplicates:
    for name, versions in sorted(actual_duplicates.items()):
        print(f"Repository: {name}")
        print(f"Found {len(versions)} copies:")
        for v in sorted(versions, key=lambda x: int(x['days_since_commit'])):
            print(f"  - {v['directory']}/{v['repo_name']}")
            print(f"    Last commit: {v['last_commit_date']} ({v['days_since_commit']} days ago)")
            print(f"    Remote: {v['remote_url']}")
        print()
else:
    print("No duplicate repositories found!")
    print()

print("=" * 80)
print("REPOSITORY CATEGORIZATION")
print("=" * 80)
print()

total_repos = len(repos)
for category, repos_list in sorted(categories.items()):
    if repos_list:
        print(f"{category.upper().replace('-', ' ')} ({len(repos_list)} repos)")
        print("-" * 80)
        for repo in sorted(repos_list, key=lambda x: x['repo_name']):
            print(f"  {repo['repo_name']} ({repo['directory']}) - {repo['last_commit_date']}")
        print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total repositories: {total_repos}")
print(f"Duplicate repository names: {len(actual_duplicates)}")
print(f"Inactive repositories (180+ days): {len(categories['archived-inactive'])}")
print()

# Save categorization to JSON for later use
categorization_data = {
    'duplicates': {k: [r['repo_path'] for r in v] for k, v in actual_duplicates.items()},
    'categories': {k: [r['repo_path'] for r in v] for k, v in categories.items() if v},
    'summary': {
        'total': total_repos,
        'duplicates': len(actual_duplicates),
        'inactive': len(categories['archived-inactive'])
    }
}

with open('/sessions/keen-gracious-wozniak/categorization.json', 'w') as f:
    json.dump(categorization_data, f, indent=2)

print("Categorization data saved to categorization.json")
