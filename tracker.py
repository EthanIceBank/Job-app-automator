"""
Tracker
-------
Logs every job (applied, skipped, error) to tracker.csv
"""

import csv
from pathlib import Path
from datetime import datetime

TRACKER_PATH = Path("tracker.csv")
FIELDNAMES = ["date", "title", "company", "location", "source", "url", "status"]


def log_job(job: dict, status: str):
    """Append a job entry to tracker.csv."""
    file_exists = TRACKER_PATH.exists()

    with open(TRACKER_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "source": job.get("source", ""),
            "url": job.get("url", ""),
            "status": status,
        })
