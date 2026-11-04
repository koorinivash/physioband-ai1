"""Make ``physioband_ml`` importable when scripts are run without ``pip install -e .``."""
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
SRC = ML_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
