"""Compatibility entry point for the native-controls simultaneous regression."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("fast-native-browser-smoke.py")),run_name="__main__")
