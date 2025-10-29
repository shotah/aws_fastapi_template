"""Pytest configuration and fixtures."""
import os
import sys

# Add src directory to Python path for test imports
# This allows tests to import modules the same way Lambda does
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
