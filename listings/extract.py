"""Extract: copy each source's data for one day into the raw zone, exactly as received.

Nothing is cleaned here. If a later step has a bug, the original data is still
on disk and can be reprocessed without asking the agencies again.
"""

import csv
import json
import os
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from listings.config import DATA_DIR

SOURCES_DIR = DATA_DIR / "sources"
RAW_DIR = DATA_DIR / "raw"
AGENCY_B_URL = os.environ.get("AGENCY_B_URL", "http://localhost:8081")


def _raw_path(source: str, run_date: str, ext: str) -> Path:
    # One folder per source and day. Re-running a day overwrites that day only.
    path = RAW_DIR / source / run_date / f"listings.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def extract_agency_a(run_date: str) -> dict:
    """Agency A drops a CSV file every day."""
    path = _raw_path("agency_a", run_date, "csv")
    shutil.copyfile(SOURCES_DIR / "agency_a" / f"{run_date}.csv", path)
    with path.open(newline="", encoding="utf-8") as f:
        records = sum(1 for _ in csv.DictReader(f))
    return {"source": "agency_a", "path": str(path), "records": records}


def extract_agency_b(run_date: str, base_url: str = AGENCY_B_URL) -> dict:
    """Agency B has an API."""
    response = requests.get(f"{base_url}/listings", params={"date": run_date}, timeout=10)
    response.raise_for_status()
    path = _raw_path("agency_b", run_date, "json")
    path.write_bytes(response.content)
    return {"source": "agency_b", "path": str(path), "records": len(json.loads(response.content)["listings"])}


def extract_agency_c(run_date: str) -> dict:
    """Agency C publishes an XML feed file."""
    path = _raw_path("agency_c", run_date, "xml")
    shutil.copyfile(SOURCES_DIR / "agency_c" / f"{run_date}.xml", path)
    return {"source": "agency_c", "path": str(path), "records": len(ET.parse(path).getroot().findall("annonce"))}
