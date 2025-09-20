#!/usr/bin/env python3
"""
Launcher script for Garrett Discovery Document Prep Tool
Run this from any directory - it will set up the correct paths
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# Import and run the main application
try:
    from main import main
    print("Starting Garrett Discovery Document Prep Tool...")
    main()
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    print("Or install dependencies: pip install -r installation/requirements.txt")
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)