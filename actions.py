import hashlib
import json
import os

from db import get_conn, init_db
from logic import analyze, load_postings

SAVED_FILE = "data/saved_resources.json"

# One free resource per skill. Step 9 will check that every link opens.
RESOURCES = {
    "SQL": {"title": "SQLBolt interactive SQL lessons", "url": "https://sqlbolt.com/"},
    "Python": {"title": "The Python Tutorial (official docs)", "url": "https://docs.python.org/3/tutorial/"},
    "Excel": {"title": "Excel help and learning (Microsoft)", "url": "https://support.microsoft.com/en-us/excel"},
    "Tableau": {"title": "Tableau Get Started tutorial", "url": "https://help.tableau.com/current/guides/get-started-tutorial/en-us/get-started-tutorial-home.htm"},
    "Power BI": {"title": "Power BI training (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/powerbi/"},
    "Statistics": {"title": "Statistics and probability (Khan Academy)", "url": "https://www.khanacademy.org/math/statistics-probability"},
    "Data Visualization": {"title": "Data Visualization course (Kaggle)", "url": "https://www.kaggle.com/learn/data-visualization"},
    "ETL": {"title": "What is ETL (IBM)", "url": "https://www.ibm.com/topics/etl"},
    "R": {"title": "swirl: learn R inside R", "url": "https://swirlstats.com/"},
    "Machine Learning": {"title": "Intro to Machine Learning (Kaggle)", "url": "https://www.kaggle.com/learn/intro-to-machine-learning"},
    "Looker": {"title": "Looker documentation (Google Cloud)", "url": "https://cloud.google.com/looker/docs"},
}


def create_input(resume_text, target_role, city, hours_per_week):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO inputs (resume_text, target_role, city, hours_per_week) "
        "VALUES (?, ?, ?, ?)",
        (resume_text, target_role, city, hours_per_week),
    )
    conn.commit()
    input_id = cur.lastrowid
    conn.close()
    return input_id


def propose_action(input_id, gaps, top_n=3):
    """Build the proposal and store it as 'pending'. Nothing is saved yet."""
    open_gaps = [g for g in gaps if g["status"] == "gap"]
    open_gaps.sort(key=lambda g: -g["posting_count"])

    items = []
    for g in open_gaps[:top_n]:
        res = RESOURCES.get(g["skill"])
        if res:
            items.append({
                "skill": g["skill"],
                "postings": g["posting_count"],
                "title": res["title"],
                "url": res["url"],
            })

    change = {"action": "save_free_resources", "destination": SAVED_FILE, "items": items}
    change_text = json.dumps(change, sort_keys=True)

    # Same input + same proposal always gives the same ID, so retries match.
    action_id = hashlib.sha1(f"{input_id}|{change_text}".encode("utf-8")).hexdigest()[:16]

    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO actions "
        "(action_id, input_id, proposed_change, approval_status) "
        "VALUES (?, ?, ?, 'pending')",
        (action_id, input_id, change_text),
    )
    conn.commit()
    conn.close()
    return {"action_id": action_id, "destination": SAVED_FILE, "items": items}


def approve(action_id):
    """Run the action once. A second call does nothing."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM actions WHERE action_id = ?", (action_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return {"result": "not_found"}

    # Only one caller can move the action from pending to executed.
    cur = conn.execute(
        "UPDATE actions SET approval_status = 'executed', "
        "approved_version = proposed_change "
        "WHERE action_id = ? AND approval_status = 'pending'",
        (action_id,),
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {
            "result": "skipped",
            "reason": f"action is already {row['approval_status']}",
        }

    change = json.loads(row["proposed_change"])
    try:
        saved = []
        if os.path.exists(SAVED_FILE):
            with open(SAVED_FILE, encoding="utf-8") as f:
                saved = json.load(f)
        for item in change["items"]:
            saved.append({"action_id": action_id, **item})
        with open(SAVED_FILE, "w", encoding="utf-8") as f:
            json.dump(saved, f, indent=2)
    except Exception as e:
        conn.execute(
            "UPDATE actions SET approval_status = 'failed' WHERE action_id = ?",
            (action_id,),
        )
        conn.commit()
        conn.close()
        return {"result": "failed", "error": str(e)}

    conn.close()
    return {"result": "executed", "saved": len(change["items"])}


def reject(action_id):
    conn = get_conn()
    cur = conn.execute(
        "UPDATE actions SET approval_status = 'rejected' "
        "WHERE action_id = ? AND approval_status = 'pending'",
        (action_id,),
    )
    conn.commit()
    conn.close()
    return {"result": "rejected" if cur.rowcount else "skipped"}


if __name__ == "__main__":
    init_db()
    if os.path.exists(SAVED_FILE):
        os.remove(SAVED_FILE)  # start each test run clean

    with open("data/resume_excel_only.txt", encoding="utf-8") as f:
        resume = f.read()

    result = analyze(load_postings("data/postings.json"), resume)
    input_id = create_input(resume, "Data Analyst", "Hyderabad", 10)
    proposal = propose_action(input_id, result["gaps"])

    print("Proposed action:", proposal["action_id"])
    print("Destination:", proposal["destination"])
    for i, item in enumerate(proposal["items"], start=1):
        print(f"  {i}. {item['skill']} ({item['postings']} postings) -> {item['url']}")

    print("\nSaved file exists before approval:", os.path.exists(SAVED_FILE))
    print("Approve (first click):", approve(proposal["action_id"]))
    print("Approve (retry):      ", approve(proposal["action_id"]))

    with open(SAVED_FILE, encoding="utf-8") as f:
        print("Items in saved file:", len(json.load(f)))