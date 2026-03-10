#!/bin/sh
set -eu
echo "=== Running tests ==="
pip install -q -e ".[test]"
pytest -m "not integration" -v
