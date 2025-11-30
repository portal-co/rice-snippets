# rice-snippets

Usable snippets of package management files extracted from the portal-co organization repositories.

## Overview

This repository contains dependency snippets extracted from `Cargo.toml` files across the [portal-co](https://github.com/portal-co) organization. These snippets can be used as templates for new Rust projects or to quickly add commonly used dependencies.

## Directory Structure

```
rice-snippets/
├── cargo-tomls/          # Full Cargo.toml files from each repository
├── snippets/
│   └── cargo/            # Extracted dependency sections
│       ├── {repo}_dependencies.toml
│       ├── {repo}_dev-dependencies.toml
│       ├── {repo}_workspace-dependencies.toml
│       └── README.md     # List of all repositories
└── scripts/
    └── download_cargo_deps.py  # Script to download and extract dependencies
```

## Usage

### Using Snippets

1. Browse the `snippets/cargo/` directory to find relevant dependency groups
2. Copy the dependencies you need into your `Cargo.toml` file
3. Adjust versions as needed

### Regenerating Snippets

To update the snippets with the latest dependencies from portal-co repositories:

```bash
python3 scripts/download_cargo_deps.py
```

## Statistics

- **96 repositories** scanned
- **92 repositories** with dependencies extracted
- **98 dependency sections** generated

## License

See [LICENSE](LICENSE) for details.
