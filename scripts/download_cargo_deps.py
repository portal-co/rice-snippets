#!/usr/bin/env python3
"""
Download Cargo.toml files from portal-co organization repositories
and extract dependency sections for templating.
"""

import os
import re
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# List of Rust repositories in portal-co organization (manually compiled from GitHub search)
RUST_REPOS = [
    "rift", "scrave", "corwake", "hermitking", "valser", "hash-based-signature",
    "embedded-llm", "axum-wist", "portal-core", "no-error", "wreck", "iob",
    "libtut", "boople", "koffle", "shufl", "crust-cage", "bf-beef",
    "portal-solutions-ai-interface", "mx6502", "wars2", "mplbeem",
    "portal-solutions-extism-compat", "wax", "dog-park-repellant", "weev",
    "stern-bijection", "elegant-pairing", "proxy-signs", "amgo", "vane",
    "corki", "gorf", "rice", "nanbox", "music-blender", "awaiter-trait",
    "panic-ub", "llvm-codegen-utils", "asm-arch", "talc", "pit-core",
    "more_waffle", "trust-ident", "ribose", "static-async-concurrency",
    "bysyncify", "otp-stream", "portal-solutions-sdk", "jsaw", "simpl",
    "embedded-chacha", "simple-encryption", "xtp-schema", "rv-emit", "sage",
    "debuff", "blang", "andes", "portal-solutions-sky", "more-pit",
    "asm-common", "rage", "rewd", "embedded-packet-io", "pupi", "fmt-fix",
    "i4delt", "tipsy", "morphic", "wasmsign3", "rv-utils", "swibb", "soda",
    "embedded-io-convert", "codegen-utils", "codegen-utils-common", "pair",
    "asim", "wasm-blitz", "jsaw-core", "pidl", "trampoline-rs", "sha3-literal",
    "waco", "pit", "sh-secgen", "minicoro-awaiters", "speet", "yonet",
    "rebornpack", "stream-sink", "arena-traits", "metapatch", "wars-pit-plugin",
    "weevy"
]

# Default branches for repos (most are 'main', some are 'master')
MASTER_REPOS = [
    "valser", "weev", "elegant-pairing", "llvm-codegen-utils", "talc",
    "more_waffle", "otp-stream", "jsaw", "simple-encryption", "sage", "soda",
    "embedded-io-convert", "codegen-utils", "pair", "pidl", "trampoline-rs",
    "pit", "rebornpack", "stream-sink"
]


def get_default_branch(repo: str) -> str:
    """Get the default branch for a repository."""
    return "master" if repo in MASTER_REPOS else "main"


def download_cargo_toml(owner: str, repo: str, branch: str) -> Optional[str]:
    """Download Cargo.toml from a GitHub repository."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/Cargo.toml"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Try alternate branch
            alt_branch = "master" if branch == "main" else "main"
            alt_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{alt_branch}/Cargo.toml"
            try:
                with urllib.request.urlopen(alt_url, timeout=10) as response:
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


def save_snippet(output_dir: Path, repo: str, section_name: str, content: str):
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


def main():
    """Main function to download and process Cargo.toml files."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    output_dir = repo_root / "snippets" / "cargo"
    cargo_tomls_dir = repo_root / "cargo-tomls"
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    cargo_tomls_dir.mkdir(parents=True, exist_ok=True)
    
    owner = "portal-co"
    stats = {
        'total_repos': len(RUST_REPOS),
        'downloaded': 0,
        'failed': 0,
        'sections_extracted': 0,
        'repos_with_deps': []
    }
    
    print(f"Downloading Cargo.toml files from {len(RUST_REPOS)} repositories...")
    print(f"Output directory: {output_dir}")
    print("-" * 60)
    
    for repo in RUST_REPOS:
        branch = get_default_branch(repo)
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
                filepath = save_snippet(output_dir, repo, section_name, section_content)
                stats['sections_extracted'] += 1
                print(f"  -> Saved {section_name} to {filepath.name}")
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Total repositories: {stats['total_repos']}")
    print(f"  Successfully downloaded: {stats['downloaded']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Dependency sections extracted: {stats['sections_extracted']}")
    print(f"  Repos with dependencies: {len(stats['repos_with_deps'])}")
    
    # Save summary
    summary_path = output_dir / "README.md"
    with open(summary_path, 'w') as f:
        f.write("# Cargo Dependency Snippets\n\n")
        f.write("This directory contains dependency sections extracted from Cargo.toml files\n")
        f.write("across the portal-co organization repositories.\n\n")
        f.write("## Usage\n\n")
        f.write("These snippets can be used as templates for new Rust projects.\n")
        f.write("Simply copy the relevant dependencies into your Cargo.toml file.\n\n")
        f.write("## Repositories with Dependencies\n\n")
        for repo in sorted(stats['repos_with_deps']):
            f.write(f"- [{repo}](https://github.com/portal-co/{repo})\n")
        f.write("\n")
        f.write(f"\n*Generated automatically by download_cargo_deps.py*\n")
    
    print(f"\nDone! Snippets saved to {output_dir}")


if __name__ == "__main__":
    main()
