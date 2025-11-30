# Cargo Dependency Snippets (Grouped)

This directory contains symlinks to deduplicated dependency snippets.
Each symlink points to a hash-based file in `cargo-hashed/`.

## Naming Convention

Symlinks are named: `{repo}_{section}_group{NN}.toml`

Where:
- `{repo}` is the repository name
- `{section}` is the dependency section (e.g., `dependencies`, `workspace-dependencies`)
- `{NN}` is the group number within that section

## Usage

These symlinks allow you to reference snippets by their source location
while the actual content is deduplicated in `cargo-hashed/`.

Total grouped snippets: 192
Unique content files: 158


*Generated automatically by download_cargo_deps.py*
