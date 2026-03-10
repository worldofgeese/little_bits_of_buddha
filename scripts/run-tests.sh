#!/bin/sh
set -eu
echo "=== Running tests ==="
# Non-editable install in CI to avoid breaking namespace packages (dapr)
pip install -q ".[test]"
pytest -m "not integration" -v
