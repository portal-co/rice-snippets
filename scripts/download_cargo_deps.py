#!/usr/bin/env python3
"""
Download Cargo.toml files from portal-co organization repositories
and extract dependency sections for templating.

Dependencies are split by logical groupings (blank lines) into separate files.
Uses SHA256 hashing for deduplication with symlinks for the naming scheme.
"""

import os
import re
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Tuple, Dict


def discover_rust_repos(owner: str, per_page: int = 100) -> List[Dict]:
    """
    Automatically discover Rust repositories in the organization using GitHub API.
    Returns a list of repository info dicts with name and default_branch.
    Raises an exception if the API fails.
    """
    repos = []
    page = 1
    
    print(f"Discovering Rust repositories in {owner}...")
    
    while True:
        url = f"https://api.github.com/search/repositories?q=org:{owner}+language:Rust&per_page={per_page}&page={page}"
        try:
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', 'rice-snippets-downloader')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                items = data.get('items', [])
                
                if not items:
                    break
                
                for item in items:
                    repos.append({
                        'name': item['name'],
                        'default_branch': item.get('default_branch', 'main'),
                        'full_name': item['full_name']
                    })
                
                # Check if there are more pages
                if len(items) < per_page:
                    break
                    
                page += 1
                
        except urllib.error.HTTPError as e:
            print(f"  [ERROR] GitHub API error: {e.code}")
            raise
        except Exception as e:
            print(f"  [ERROR] Failed to discover repos: {e}")
            raise
    
    if not repos:
        raise RuntimeError("No repositories found via GitHub API")
    
    print(f"  Found {len(repos)} Rust repositories")
    return repos


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of the content (excluding metadata comments)."""
    # Strip leading comments that contain metadata
    lines = content.split('\n')
    content_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip metadata comments at the start
        if stripped.startswith('# Source:') or stripped.startswith('# Section:') or stripped.startswith('# Auto-generated'):
            continue
        content_lines.append(line)
    
    # Remove leading/trailing whitespace from the combined content
    clean_content = '\n'.join(content_lines).strip()
    return hashlib.sha256(clean_content.encode('utf-8')).hexdigest()


def download_cargo_toml(owner: str, repo: str, branch: str) -> Optional[str]:
    """Download Cargo.toml from a GitHub repository."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/Cargo.toml"
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'rice-snippets-downloader')
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Try alternate branch
            alt_branch = "master" if branch == "main" else "main"
            alt_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{alt_branch}/Cargo.toml"
            try:
                req = urllib.request.Request(alt_url)
                req.add_header('User-Agent', 'rice-snippets-downloader')
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.read().decode('utf-8')
            except urllib.error.HTTPError:
                print(f"  [SKIP] No Cargo.toml found in {repo}")
                return None
        print(f"  [ERROR] HTTP {e.code} for {repo}")
        return None
    except Exception as e:
        print(f"  [ERROR] {e} for {repo}")
        return None


def extract_dependency_sections(content: str) -> dict:
    """
    Extract dependency sections from Cargo.toml content.
    Returns a dict with section names as keys and section content as values.
    """
    sections = {}
    
    # Patterns for different dependency sections
    section_patterns = [
        (r'\[dependencies\]', 'dependencies'),
        (r'\[dev-dependencies\]', 'dev-dependencies'),
        (r'\[build-dependencies\]', 'build-dependencies'),
        (r'\[workspace\.dependencies\]', 'workspace.dependencies'),
    ]
    
    lines = content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        # Check if this line starts a new section
        new_section = None
        for pattern, name in section_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                new_section = name
                break
        
        # Check if this is any other section header
        if new_section is None and re.match(r'^\[.*\]$', line.strip()):
            # End current section if we were in one
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = None
            current_content = []
            continue
        
        if new_section:
            # Save previous section if exists
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = new_section
            current_content = [line]
        elif current_section:
            current_content.append(line)
    
    # Don't forget the last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections


def split_by_blank_lines(content: str) -> List[str]:
    """
    Split content into groups separated by blank lines.
    Returns a list of non-empty groups.
    Handles multi-line TOML entries (entries spanning multiple lines).
    """
    lines = content.split('\n')
    groups = []
    current_group = []
    in_multiline = False
    bracket_count = 0
    
    # Skip the section header line (e.g., [dependencies])
    start_idx = 0
    for i, line in enumerate(lines):
        if re.match(r'^\[.*\]$', line.strip()):
            start_idx = i + 1
            break
    
    for line in lines[start_idx:]:
        stripped = line.strip()
        
        # Track multiline entries (count brackets)
        if not in_multiline:
            # Check if this line starts a multi-line entry
            open_count = line.count('[') + line.count('{')
            close_count = line.count(']') + line.count('}')
            if open_count > close_count:
                in_multiline = True
                bracket_count = open_count - close_count
        else:
            # Update bracket count
            open_count = line.count('[') + line.count('{')
            close_count = line.count(']') + line.count('}')
            bracket_count += open_count - close_count
            if bracket_count <= 0:
                in_multiline = False
                bracket_count = 0
        
        # Check for blank line (empty or only whitespace)
        # Only split on blank lines if we're not in a multi-line entry
        if not stripped and not in_multiline:
            if current_group:
                # Filter out comment-only groups and malformed snippets
                has_deps = any(
                    l.strip() and not l.strip().startswith('#') and '=' in l
                    for l in current_group
                )
                if has_deps:
                    groups.append('\n'.join(current_group))
                current_group = []
        else:
            current_group.append(line)
    
    # Don't forget the last group
    if current_group:
        has_deps = any(
            l.strip() and not l.strip().startswith('#') and '=' in l
            for l in current_group
        )
        if has_deps:
            groups.append('\n'.join(current_group))
    
    return groups


def save_snippet(output_dir: Path, repo: str, section_name: str, content: str) -> Path:
    """Save a dependency snippet to a file."""
    # Create a safe filename
    safe_section = section_name.replace('.', '-').replace('/', '-')
    filename = f"{repo}_{safe_section}.toml"
    filepath = output_dir / filename
    
    with open(filepath, 'w') as f:
        f.write(f"# Source: portal-co/{repo}\n")
        f.write(f"# Section: [{section_name}]\n")
        f.write(f"# Auto-generated - do not edit\n\n")
        f.write(content)
        f.write('\n')
    
    return filepath


def save_hashed_snippet(hash_dir: Path, content: str, sources: List[str]) -> Tuple[Path, str]:
    """
    Save a dependency snippet to a hash-based file.
    Returns the filepath and the hash.
    """
    content_hash = compute_content_hash(content)
    # Use first 16 chars of hash for filename (64 bits, still unique enough)
    short_hash = content_hash[:16]
    filename = f"{short_hash}.toml"
    filepath = hash_dir / filename
    
    # Only write if file doesn't exist (deduplication)
    if not filepath.exists():
        with open(filepath, 'w') as f:
            f.write(f"# Hash: {content_hash}\n")
            f.write(f"# Sources: {', '.join(sources)}\n")
            f.write(f"# Auto-generated - do not edit\n\n")
            f.write(content)
            f.write('\n')
    else:
        # Update sources in existing file
        with open(filepath, 'r') as f:
            existing_content = f.read()
        
        # Parse existing sources
        existing_sources = []
        for line in existing_content.split('\n'):
            if line.startswith('# Sources:'):
                existing_sources = [s.strip() for s in line[10:].split(',')]
                break
        
        # Add new sources
        all_sources = list(set(existing_sources + sources))
        
        # Rewrite with updated sources
        lines = existing_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# Sources:'):
                lines[i] = f"# Sources: {', '.join(sorted(all_sources))}"
                break
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
    
    return filepath, short_hash


def create_symlink(symlink_path: Path, target_path: Path):
    """Create a symlink, handling existing files."""
    # Remove existing file/symlink if it exists
    if symlink_path.exists() or symlink_path.is_symlink():
        symlink_path.unlink()
    
    # Create relative symlink
    rel_target = os.path.relpath(target_path, symlink_path.parent)
    symlink_path.symlink_to(rel_target)


def save_grouped_snippet(grouped_dir: Path, hash_dir: Path, repo: str, section_name: str, 
                         group_index: int, content: str, hash_registry: Dict[str, List[str]]) -> Tuple[Path, str]:
    """
    Save a grouped dependency snippet using hash-based deduplication.
    Creates a symlink from the named file to the hash-based file.
    Returns the symlink path and hash.
    """
    # Compute hash of the content
    content_hash = compute_content_hash(content)
    short_hash = content_hash[:16]
    
    # Source identifier for this snippet
    safe_section = section_name.replace('.', '-').replace('/', '-')
    source_id = f"{repo}/{safe_section}/group{group_index:02d}"
    
    # Track sources for this hash
    if short_hash not in hash_registry:
        hash_registry[short_hash] = []
    hash_registry[short_hash].append(source_id)
    
    # Save to hash-based file
    hash_file, _ = save_hashed_snippet(hash_dir, content, [source_id])
    
    # Create symlink with the friendly name
    symlink_name = f"{repo}_{safe_section}_group{group_index:02d}.toml"
    symlink_path = grouped_dir / symlink_name
    create_symlink(symlink_path, hash_file)
    
    return symlink_path, short_hash


def main():
    """Main function to download and process Cargo.toml files."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    output_dir = repo_root / "snippets" / "cargo"
    grouped_dir = repo_root / "snippets" / "cargo-grouped"
    hash_dir = repo_root / "snippets" / "cargo-hashed"
    cargo_tomls_dir = repo_root / "cargo-tomls"
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped_dir.mkdir(parents=True, exist_ok=True)
    hash_dir.mkdir(parents=True, exist_ok=True)
    cargo_tomls_dir.mkdir(parents=True, exist_ok=True)
    
    owner = "portal-co"
    
    # Automatically discover Rust repositories
    repos = discover_rust_repos(owner)
    
    if not repos:
        print("ERROR: No repositories found. Exiting.")
        import sys
        sys.exit(1)
    
    stats = {
        'total_repos': len(repos),
        'downloaded': 0,
        'failed': 0,
        'sections_extracted': 0,
        'groups_extracted': 0,
        'unique_hashes': 0,
        'repos_with_deps': []
    }
    
    # Registry to track hash -> sources mapping
    hash_registry: Dict[str, List[str]] = {}
    
    print(f"\nDownloading Cargo.toml files from {len(repos)} repositories...")
    print(f"Output directory: {output_dir}")
    print(f"Grouped directory: {grouped_dir}")
    print(f"Hash directory: {hash_dir}")
    print("-" * 60)
    
    for repo_info in repos:
        repo = repo_info['name']
        branch = repo_info['default_branch']
        print(f"Processing {repo}...")
        
        content = download_cargo_toml(owner, repo, branch)
        if content is None:
            stats['failed'] += 1
            continue
        
        stats['downloaded'] += 1
        
        # Save the full Cargo.toml
        cargo_toml_path = cargo_tomls_dir / f"{repo}_Cargo.toml"
        with open(cargo_toml_path, 'w') as f:
            f.write(f"# Source: portal-co/{repo}\n")
            f.write(f"# Auto-generated - do not edit\n\n")
            f.write(content)
        
        # Extract dependency sections
        sections = extract_dependency_sections(content)
        
        if sections:
            stats['repos_with_deps'].append(repo)
            for section_name, section_content in sections.items():
                # Save the full section
                filepath = save_snippet(output_dir, repo, section_name, section_content)
                stats['sections_extracted'] += 1
                print(f"  -> Saved {section_name} to {filepath.name}")
                
                # Split by blank lines and save grouped snippets with hash-based dedup
                groups = split_by_blank_lines(section_content)
                for i, group in enumerate(groups, 1):
                    symlink_path, content_hash = save_grouped_snippet(
                        grouped_dir, hash_dir, repo, section_name, i, group, hash_registry
                    )
                    stats['groups_extracted'] += 1
                    print(f"     -> Group {i}: {symlink_path.name} -> {content_hash}.toml")
    
    # Count unique hashes
    stats['unique_hashes'] = len(hash_registry)
    duplicates = sum(1 for sources in hash_registry.values() if len(sources) > 1)
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Total repositories: {stats['total_repos']}")
    print(f"  Successfully downloaded: {stats['downloaded']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Dependency sections extracted: {stats['sections_extracted']}")
    print(f"  Grouped snippets created: {stats['groups_extracted']}")
    print(f"  Unique content hashes: {stats['unique_hashes']}")
    print(f"  Duplicated snippets: {duplicates}")
    print(f"  Repos with dependencies: {len(stats['repos_with_deps'])}")
    
    # Save summary for main snippets
    summary_path = output_dir / "README.md"
    with open(summary_path, 'w') as f:
        f.write("# Cargo Dependency Snippets\n\n")
        f.write("This directory contains dependency sections extracted from Cargo.toml files\n")
        f.write("across the portal-co organization repositories.\n\n")
        f.write("## Usage\n\n")
        f.write("These snippets can be used as templates for new Rust projects.\n")
        f.write("Simply copy the relevant dependencies into your Cargo.toml file.\n\n")
        f.write("For smaller, logically grouped snippets, see the `cargo-grouped/` directory.\n\n")
        f.write("For deduplicated hash-based snippets, see the `cargo-hashed/` directory.\n\n")
        f.write("## Repositories with Dependencies\n\n")
        for repo in sorted(stats['repos_with_deps']):
            f.write(f"- [{repo}](https://github.com/portal-co/{repo})\n")
        f.write("\n")
        f.write(f"\n*Generated automatically by download_cargo_deps.py*\n")
    
    # Save summary for grouped snippets
    grouped_summary_path = grouped_dir / "README.md"
    with open(grouped_summary_path, 'w') as f:
        f.write("# Cargo Dependency Snippets (Grouped)\n\n")
        f.write("This directory contains symlinks to deduplicated dependency snippets.\n")
        f.write("Each symlink points to a hash-based file in `cargo-hashed/`.\n\n")
        f.write("## Naming Convention\n\n")
        f.write("Symlinks are named: `{repo}_{section}_group{NN}.toml`\n\n")
        f.write("Where:\n")
        f.write("- `{repo}` is the repository name\n")
        f.write("- `{section}` is the dependency section (e.g., `dependencies`, `workspace-dependencies`)\n")
        f.write("- `{NN}` is the group number within that section\n\n")
        f.write("## Usage\n\n")
        f.write("These symlinks allow you to reference snippets by their source location\n")
        f.write("while the actual content is deduplicated in `cargo-hashed/`.\n\n")
        f.write(f"Total grouped snippets: {stats['groups_extracted']}\n")
        f.write(f"Unique content files: {stats['unique_hashes']}\n\n")
        f.write(f"\n*Generated automatically by download_cargo_deps.py*\n")
    
    # Save summary for hash-based snippets
    hash_summary_path = hash_dir / "README.md"
    with open(hash_summary_path, 'w') as f:
        f.write("# Cargo Dependency Snippets (Hash-Based)\n\n")
        f.write("This directory contains deduplicated dependency snippets identified by SHA256 hash.\n\n")
        f.write("## Naming Convention\n\n")
        f.write("Files are named: `{hash}.toml` where `{hash}` is the first 16 characters of the SHA256 hash.\n\n")
        f.write("## Deduplication\n\n")
        f.write("Multiple repositories may share the same dependency groups.\n")
        f.write("Each file contains a `# Sources:` comment listing all sources that share this content.\n\n")
        f.write("## Usage\n\n")
        f.write("Reference these files directly by hash for stable, content-addressable snippets.\n")
        f.write("Or use the symlinks in `cargo-grouped/` for human-readable names.\n\n")
        f.write(f"Total unique snippets: {stats['unique_hashes']}\n\n")
        
        # List duplicated snippets
        if duplicates > 0:
            f.write("## Shared Snippets\n\n")
            f.write("The following snippets are shared by multiple sources:\n\n")
            for content_hash, sources in sorted(hash_registry.items()):
                if len(sources) > 1:
                    f.write(f"### `{content_hash}.toml`\n")
                    for source in sorted(sources):
                        f.write(f"- {source}\n")
                    f.write("\n")
        
        f.write(f"\n*Generated automatically by download_cargo_deps.py*\n")
    
    print(f"\nDone! Snippets saved to {output_dir}, {grouped_dir}, and {hash_dir}")


if __name__ == "__main__":
    main()
