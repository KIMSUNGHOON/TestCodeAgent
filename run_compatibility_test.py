#!/usr/bin/env python3
"""Run compatibility tests - Cross-platform test runner"""

import subprocess
import sys
import os

# Change to backend directory
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
os.chdir(backend_dir)

# Run pytest
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_compatibility.py", "-v", "--tb=short"],
    capture_output=False
)

sys.exit(result.returncode)
