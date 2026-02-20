"""
Entry-point launcher for the PySide2 frontend.

Run from the frontend_pyside2/ directory:
    python run.py

Or from any location:
    python /path/to/frontend_pyside2/run.py
"""
import sys
import os

# Ensure src/ is on the path regardless of where we are launched from
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from main import main

if __name__ == "__main__":
    sys.exit(main())
