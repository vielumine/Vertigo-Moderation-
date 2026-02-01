"""Convenience entrypoint for running the Vertigo bot.

Preferred entrypoint is :mod:`vertigo.main`.
"""

import sys
import os

# Add vertigo directory to path so absolute imports and cog loading work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertigo'))

from main import run


if __name__ == "__main__":
    run()
