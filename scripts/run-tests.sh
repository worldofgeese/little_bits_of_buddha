#!/bin/sh
set -eu
echo "=== Running tests ==="
# Diagnostic: show python and pip info
python --version
pip --version

# Install with no cache to avoid stale packages
pip install --no-cache-dir -q ".[test]"

# Diagnostic: verify dapr namespace package
echo "=== Verifying dapr import ==="
python -c "
import sys
print('sys.path:', sys.path[:5])
import dapr
print('dapr type:', type(dapr))
print('dapr file:', getattr(dapr, '__file__', 'NONE'))
print('dapr path:', getattr(dapr, '__path__', 'NO PATH'))
from dapr.actor import ActorId
print('dapr.actor OK')
"

pytest -m "not integration" -v
