#!/usr/bin/env sh
# CI Preflight — fail fast with clear messages when optional deps are missing.
# Called by run-tests.sh and run-lint.sh before doing real work.
set -e

MISSING=""

# Check core dapr
python3 -c "import dapr" 2>/dev/null || MISSING="$MISSING dapr"

# Check optional dapr extensions (warn only — tests marked @integration skip these)
python3 -c "from dapr.ext.workflow import DaprWorkflowContext" 2>/dev/null || \
  echo "⚠️  dapr-ext-workflow not installed — @integration tests will be skipped"

# Check numpy (required for langcache tests)
python3 -c "import numpy" 2>/dev/null || MISSING="$MISSING numpy"

# Check trio (required for async tests)
python3 -c "import trio" 2>/dev/null || MISSING="$MISSING trio"

# Check pytest
python3 -c "import pytest" 2>/dev/null || MISSING="$MISSING pytest"

if [ -n "$MISSING" ]; then
  echo "❌ CI preflight failed — missing required packages:$MISSING"
  echo "   Run: pip install -e '.[test]'"
  exit 1
fi

echo "✅ CI preflight passed"
