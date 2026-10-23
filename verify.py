import json
import os

import requests

from db import get_conn, init_db
from logic import dedup, load_postings

HEADERS = {"User-Agent": "Mozilla/5.0 (SkillGapAnalyzer demo)"}
SAVED_FILE = "data/saved_resources.json"


def check_url(url, kind, save=True):
    """Request the URL and record what was actually observed."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        status = resp.status_code
        live = 1 if status < 400 else 0
    except requests.RequestException:
        status = 0  # no response at all
        live = 0

    if save:
        conn = get_conn()
        conn.execute(
            "INSERT INTO verifications (url, kind, is_live, status_code) "
            "VALUES (?, ?, ?, ?)",
            (url, kind, live, status),
        )
        conn.commit()
        conn.close()
    return {"url": url, "kind": kind, "is_live": live, "status_code": status}


def verify_postings(postings):
    return [check_url(p["url"], "posting") for p in postings]


def verify_resources(path=SAVED_FILE):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    urls = sorted({item["url"] for item in saved})
    return [check_url(u, "resource") for u in urls]


def print_report(label, results):
    live = sum(r["is_live"] for r in results)
    print(f"{label}: {live}/{len(results)} live")
    for r in results:
        if not r["is_live"]:
            print(f"  FAILED  status={r['status_code']}  {r['url']}")


if __name__ == "__main__":
    init_db()
    unique = dedup(load_postings("data/postings.json"))

    print_report("Postings ", verify_postings(unique))
    print_report("Resources", verify_resources())

    # Sanity check: the verifier must report a dead link as dead.
    fake = check_url("http://127.0.0.1:5000/job/J999", "posting", save=False)
    print("\nSanity check (fake posting J999):",
          "dead, as expected" if not fake["is_live"] else "WRONG: reported live",
          f"(status {fake['status_code']})")