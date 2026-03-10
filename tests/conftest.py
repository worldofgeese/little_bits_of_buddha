"""pytest configuration for little_bits_of_buddha tests.

This conftest adds the project root to sys.path, allowing tests to use
"from src.module import ..." imports without breaking dapr's namespace
package resolution.

Background:
- dapr is a namespace package (multiple pip packages share the "dapr" namespace)
- Adding "src/" to sys.path via pytest pythonpath config broke dapr imports
- This conftest adds the project ROOT instead, preserving namespace packages
"""

import sys
from pathlib import Path

# Add project root to sys.path so "from src." imports work
# Append (not insert) to avoid shadowing installed packages like dapr
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
