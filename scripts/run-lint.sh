#!/bin/sh
set -eu
echo "=== Running lint ==="
pip install -q -e ".[dev]"
ruff check src/
ty check src/
