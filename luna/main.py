"""Luna bot bootstrap - redirects to app.py."""

from __future__ import annotations

import sys
import os

# Add current directory to path so absolute imports work
sys.path.insert(0, os.path.dirname(__file__))

from app import run


if __name__ == "__main__":
    run()
