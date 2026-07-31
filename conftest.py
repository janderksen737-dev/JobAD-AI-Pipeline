"""Stellt sicher, dass die Repo-Root-Packages (config, engine, ...) importierbar sind."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
