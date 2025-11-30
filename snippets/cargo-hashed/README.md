# Cargo Dependency Snippets (Hash-Based)

This directory contains deduplicated dependency snippets identified by SHA256 hash.

## Naming Convention

Files are named: `{hash}.toml` where `{hash}` is the first 16 characters of the SHA256 hash.

## Deduplication

Multiple repositories may share the same dependency groups.
Each file contains a `# Sources:` comment listing all sources that share this content.

## Usage

Reference these files directly by hash for stable, content-addressable snippets.
Or use the symlinks in `cargo-grouped/` for human-readable names.

Total unique snippets: 158

## Shared Snippets

The following snippets are shared by multiple sources:

### `06905eeee9c8ab48.toml`
- asim/workspace-dependencies/group03
- speet/workspace-dependencies/group02
- wasm-blitz/workspace-dependencies/group02

### `154baa3c2e044d8a.toml`
- gorf/workspace-dependencies/group04
- rebornpack/workspace-dependencies/group05

### `2cf1cbeb898df4db.toml`
- gorf/workspace-dependencies/group15
- rebornpack/workspace-dependencies/group16

### `3048315dc6ef9caf.toml`
- gorf/workspace-dependencies/group14
- rebornpack/workspace-dependencies/group14

### `4bddb1bbdacbf8a7.toml`
- asim/workspace-dependencies/group04
- vane/workspace-dependencies/group04

### `4c71e2b66d49325a.toml`
- gorf/workspace-dependencies/group02
- rebornpack/workspace-dependencies/group01

### `607feba683d70680.toml`
- jsaw/workspace-dependencies/group02
- waco/workspace-dependencies/group04

### `6eb94338ba6a87f7.toml`
- andes/workspace-dependencies/group01
- jsaw-core/workspace-dependencies/group07
- jsaw/workspace-dependencies/group05
- rage/workspace-dependencies/group01
- rewd/workspace-dependencies/group01
- swibb/workspace-dependencies/group01

### `7d415883c770c193.toml`
- gorf/workspace-dependencies/group09
- rebornpack/workspace-dependencies/group09

### `8e3b1326bfeb53b4.toml`
- gorf/workspace-dependencies/group13
- rebornpack/workspace-dependencies/group13
- soda/workspace-dependencies/group07

### `8ec8c3752264b395.toml`
- gorf/workspace-dependencies/group10
- rebornpack/workspace-dependencies/group10

### `94cdd65851065109.toml`
- gorf/workspace-dependencies/group18
- talc/workspace-dependencies/group04

### `992ca205bbf137d1.toml`
- jsaw-core/workspace-dependencies/group03
- jsaw/workspace-dependencies/group04

### `a489cc4573ccbcc8.toml`
- jsaw-core/workspace-dependencies/group04
- jsaw/workspace-dependencies/group08

### `a876ae7a986ab20b.toml`
- gorf/workspace-dependencies/group03
- rebornpack/workspace-dependencies/group04

### `afcb1dee485a0e6c.toml`
- gorf/workspace-dependencies/group12
- rebornpack/workspace-dependencies/group12
- soda/workspace-dependencies/group06

### `bf19b21048346cf3.toml`
- vane/workspace-dependencies/group07
- weevy/workspace-dependencies/group01

### `c0b5a457a663a736.toml`
- gorf/workspace-dependencies/group11
- rebornpack/workspace-dependencies/group11

### `c21c23d30362d493.toml`
- fmt-fix/dependencies/group01
- mplbeem/dependencies/group01

### `d4d0bb89a2046d6b.toml`
- speet/workspace-dependencies/group01
- wasm-blitz/workspace-dependencies/group01
- wax/workspace-dependencies/group01

### `dc83dd6b7dbfad61.toml`
- gorf/workspace-dependencies/group17
- rebornpack/workspace-dependencies/group18

### `e2c4fa5aac8ce631.toml`
- gorf/workspace-dependencies/group08
- rebornpack/workspace-dependencies/group08

### `eb4804c0adbd4779.toml`
- speet/workspace-dependencies/group03
- vane/workspace-dependencies/group03

### `f12fec5c7714687a.toml`
- gorf/workspace-dependencies/group16
- rebornpack/workspace-dependencies/group17
- soda/workspace-dependencies/group10

### `f5c5c6728b33a316.toml`
- andes/workspace-dependencies/group02
- rewd/workspace-dependencies/group02


*Generated automatically by download_cargo_deps.py*
