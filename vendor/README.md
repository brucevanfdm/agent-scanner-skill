# Vendor Directory

This skill supports two offline modes:

1. Embedded mode (default):
- Uses bundled source in `embedded/skill_scanner/`
- Uses bundled compatibility modules in `vendor/python/`
- No network and no external package installation required
- Includes a compatibility `yara` shim, so native YARA rules are not executed in this mode

2. Wheelhouse mode (optional):
- Put wheels into `vendor/wheels/`
- Install strictly from local wheels with `scripts/install-scanner.sh`
- Useful when you need native `yara-python` or full API dependencies

## Build wheelhouse on a connected machine

```bash
./scripts/build-vendor-wheelhouse.sh
```

Then copy the whole skill folder to offline environments.
