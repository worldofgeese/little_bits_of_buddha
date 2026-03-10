#!/bin/sh
set -eu
echo "=== Running lint ==="
# Install all deps (not just dev) so ty can resolve imports
pip install -q ".[dev]"
ruff check src/
# ty needs to find all packages; point it at the install location
ty check src/
