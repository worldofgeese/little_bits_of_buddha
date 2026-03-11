#!/bin/sh
set -eu
echo "=== Running tests ==="
python --version
pip --version

# Install with no cache to avoid stale packages
pip install --no-cache-dir -q ".[test]"

# Preflight: verify required deps are importable
sh scripts/check-ci-preflight.sh

pytest -m "not integration" -v
