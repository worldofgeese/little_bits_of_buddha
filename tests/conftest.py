"""pytest configuration for little_bits_of_buddha tests.

Adds project root to END of sys.path so 'from src.' imports work
without shadowing installed packages like dapr.
"""

import sys
import os

# Get project root (parent of tests dir)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
