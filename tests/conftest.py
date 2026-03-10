"""pytest configuration for little_bits_of_buddha tests.

Adds project root to END of sys.path so 'from src.' imports work
without shadowing installed packages like dapr.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys_path_str = str(project_root)
if sys_path_str not in sys.path:
    sys.path.append(sys_path_str)
