"""Where the pipeline keeps its data.

The location comes from the environment, so the same code can run against a
test folder on a laptop and against real storage on a server.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("LISTINGS_DATA_DIR", PROJECT_ROOT / "data"))
