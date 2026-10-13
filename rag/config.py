import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Paths come from the environment so the same code runs on a laptop and on a server.
DATA_DIR = Path(os.environ.get("LISTINGS_DATA_DIR", PROJECT_ROOT / "data"))
INDEX_DIR = Path(os.environ.get("RAG_INDEX_DIR", DATA_DIR / "index"))
EVAL_FILE = Path(os.environ.get("RAG_EVAL_FILE", PROJECT_ROOT / "data" / "eval" / "golden.jsonl"))

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
TOP_K = 3

ANSWER_MODEL = "claude-opus-5-5"
