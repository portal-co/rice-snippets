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
│   └── cargo-grouped/        # Dependencies split by logical groups (blank lines)
│       ├── {repo}_{section}_group{NN}.toml
│       └── README.md
└── scripts/
    └── download_cargo_deps.py  # Script to download and extract dependencies
```

## Usage

### Using Full Section Snippets

Browse `snippets/cargo/` for complete dependency sections from each repository.

### Using Grouped Snippets

Browse `snippets/cargo-grouped/` for smaller, logically grouped dependency sets. 
These are split by blank lines in the original Cargo.toml files, allowing you to 
copy just the related dependencies you need.

Example: `gorf_workspace-dependencies_group03.toml` contains:
```toml
spin-sdk = "3.0.1"
url = { version = "2", features = ["serde"] }
dumpster = "0.1.2"
```

### Regenerating Snippets

To update the snippets with the latest dependencies from portal-co repositories:

```bash
python3 scripts/download_cargo_deps.py
```

## Statistics

- **96 repositories** scanned
- **92 repositories** with dependencies extracted
- **98 dependency sections** generated
- **193 grouped snippets** created

## License

See [LICENSE](LICENSE) for details.
