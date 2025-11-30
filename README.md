# rice-snippets

Usable snippets of package management files extracted from the portal-co organization repositories.

## Overview

This repository contains dependency snippets extracted from `Cargo.toml` files across the [portal-co](https://github.com/portal-co) organization. These snippets can be used as templates for new Rust projects or to quickly add commonly used dependencies.

## Directory Structure

```
rice-snippets/
├── cargo-tomls/              # Full Cargo.toml files from each repository
├── snippets/
│   ├── cargo/                # Full extracted dependency sections
│   │   ├── {repo}_dependencies.toml
│   │   ├── {repo}_dev-dependencies.toml
│   │   ├── {repo}_workspace-dependencies.toml
│   │   └── README.md
│   ├── cargo-grouped/        # Symlinks to hash-based snippets
│   │   ├── {repo}_{section}_group{NN}.toml -> ../cargo-hashed/{hash}.toml
│   │   └── README.md
│   └── cargo-hashed/         # Deduplicated snippets by SHA256 hash
│       ├── {hash}.toml
│       └── README.md
└── scripts/
    └── download_cargo_deps.py  # Script to download and extract dependencies
```

## Usage

### Using Full Section Snippets

Browse `snippets/cargo/` for complete dependency sections from each repository.

### Using Grouped Snippets (by name)

Browse `snippets/cargo-grouped/` for smaller, logically grouped dependency sets.
These are symlinks to deduplicated content in `cargo-hashed/`.

Example: `gorf_workspace-dependencies_group03.toml` links to a shared snippet.

### Using Hash-Based Snippets (deduplicated)

Browse `snippets/cargo-hashed/` for unique, content-addressable snippets.
These are identified by their SHA256 hash and can be referenced directly.
Shared snippets list all their sources in the file header.

### Regenerating Snippets

The script automatically discovers Rust repositories in the portal-co organization:

```bash
python3 scripts/download_cargo_deps.py
```

## Statistics

- **96 repositories** scanned
- **92 repositories** with dependencies extracted
- **98 dependency sections** generated
- **192 grouped snippets** created
- **158 unique content hashes** (25 shared across multiple sources)

## License

See [LICENSE](LICENSE) for details.
