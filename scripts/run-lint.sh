#!/bin/sh
set -eu
echo "=== Running lint ==="
pip install -q ".[dev]"

# Preflight: verify core deps
sh scripts/check-ci-preflight.sh || true  # lint doesn't need test deps, warn only

ruff check src/
ty check src/
