"""Pytest configuration for FitFindr tests."""

import os
import sys

# Add the project root to sys.path so tests can import tools, agent, app, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
