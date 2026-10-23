import hashlib
import json
import re

# Each skill has a list of ways it can be written in a posting.
SKILLS = {
    "SQL": [r"\bsql\b", r"\bpostgresql\b", r"\bmysql\b"],
    "Excel": [r"\bexcel\b"],
    "Python": [r"\bpython\b"],
    "Tableau": [r"\btableau\b"],
    "Power BI": [r"\bpower\s?bi\b"],
    "Statistics": [r"\bstatistic(s|al)\b"],
    "Data Visualization": [r"\bdata visuali[sz]ation\b"],
    "ETL": [r"\betl\b"],
    "R": [r"\bR\b"],
    "Machine Learning": [r"\bmachine learning\b"],
    "Looker": [r"\blooker\b"],
}

# "R" must match only a capital R, or it would match any lone letter r.
CASE_SENSITIVE = {"R"}


def load_postings(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalise(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def make_dedup_key(posting):
    raw = "|".join(
        normalise(posting[field]) for field in ("company", "title", "city")
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def dedup(postings):
    """Keep the first posting for each company + title + city."""
    seen = {}
    for p in postings:
        key = make_dedup_key(p)
        if key not in seen:
            p = dict(p)
            p["dedup_key"] = key
            seen[key] = p
    return list(seen.values())


def skills_in_text(text):
    """Return the set of skills found in a piece of text."""
    found = set()
    for skill, patterns in SKILLS.items():
        flags = 0 if skill in CASE_SENSITIVE else re.IGNORECASE
        if any(re.search(p, text, flags) for p in patterns):
            found.add(skill)
    return found


def count_skills(postings):
    """Count each skill once per posting, and keep the posting IDs."""
    counts = {}
    for p in postings:
        for skill in skills_in_text(p["description"]):
            entry = counts.setdefault(skill, {"count": 0, "posting_ids": []})
            entry["count"] += 1
            entry["posting_ids"].append(p["id"])
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]["count"]))

def find_evidence(resume_text, skill):
    """Return the resume line that mentions the skill, or None."""
    for line in resume_text.splitlines():
        if skill in skills_in_text(line):
            return line.strip()
    return None


def find_gaps(resume_text, skill_counts):
    """Compare each skill employers ask for with the resume.
    This function only reads the resume. It never edits it."""
    results = []
    resume_missing = not resume_text.strip()

    for skill, info in skill_counts.items():
        evidence = None
        if resume_missing:
            status = "uncertain"
            reason = "Resume is empty, so there is no evidence to compare."
        else:
            evidence = find_evidence(resume_text, skill)
            if evidence:
                status = "covered"
                reason = "Resume mentions this skill."
            else:
                status = "gap"
                reason = (
                    f"Not found in resume; asked for in "
                    f"{info['count']} postings."
                )
        results.append({
            "skill": skill,
            "posting_count": info["count"],
            "status": status,
            "evidence": evidence,
            "reason": reason,
        })
    return results

MIN_POSTINGS = 5


def analyze(raw_postings, resume_text, target_role="Data Analyst", city="Hyderabad"):
    """Run the whole analysis, or stop and ask if there is too little evidence."""
    unique = dedup(raw_postings)

    # TC4: too few postings. Stop and ask. Do not widen silently.
    if len(unique) < MIN_POSTINGS:
        return {
            "status": "needs_confirmation",
            "postings_found": len(unique),
            "message": (
                f"Only {len(unique)} unique posting(s) found for "
                f"'{target_role}' in {city}. That is fewer than {MIN_POSTINGS}, "
                f"so the skill counts would be unreliable. "
                f"Should I widen the city or the role? Nothing has been changed."
            ),
            "options": ["widen_city", "widen_role", "keep_as_is"],
        }

    counts = count_skills(unique)
    gaps = find_gaps(resume_text, counts)
    return {
        "status": "ok",
        "postings_found": len(unique),
        "skill_counts": counts,
        "gaps": gaps,
    }


if __name__ == "__main__":
    with open("data/resume_excel_only.txt", encoding="utf-8") as f:
        resume = f.read()

    print("=== Run 1: full board (30 unique postings) ===")
    r1 = analyze(load_postings("data/postings.json"), resume)
    print("status:", r1["status"])
    print("postings used:", r1["postings_found"])

    print("\n=== Run 2: small board (TC4) ===")
    r2 = analyze(load_postings("data/postings_few.json"), resume)
    print("status:", r2["status"])
    print("postings used:", r2["postings_found"])
    print("message:", r2["message"])
    print("options:", r2["options"])
    print("skill counts computed:", "skill_counts" in r2)