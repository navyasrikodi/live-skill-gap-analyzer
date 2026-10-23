import hashlib
import json
import sys

from db import get_conn, init_db
from logic import (
    analyze,
    count_skills,
    dedup,
    find_gaps,
    load_postings,
    make_dedup_key,
    skills_in_text,
)

RESUME_PATH = "data/resume_excel_only.txt"
RESULTS = []


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def record(test_case, scenario, expected, actual, evidence, problems):
    passed = not problems
    if problems:
        evidence = evidence + " | PROBLEMS: " + "; ".join(problems)
    RESULTS.append({
        "test_case": test_case,
        "scenario": scenario,
        "expected": expected,
        "actual": actual,
        "evidence": evidence,
        "passed": passed,
    })
    conn = get_conn()
    conn.execute(
        "INSERT INTO test_runs (test_case, input_desc, expected, actual, evidence, passed) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_case, scenario, expected, actual, evidence, 1 if passed else 0),
    )
    conn.commit()
    conn.close()


def tc1():
    raw = load_postings("data/postings.json")
    thirty = dedup(raw)
    counts = count_skills(thirty)
    problems = []

    if len(thirty) != 30:
        problems.append(f"expected 30 postings, got {len(thirty)}")
    if not all("data analyst" in p["title"].lower() for p in thirty):
        problems.append("a posting is not a Data Analyst role")
    if not counts:
        problems.append("no skills were counted")

    for skill, info in counts.items():
        if info["count"] != len(info["posting_ids"]):
            problems.append(f"{skill}: count does not match its posting IDs")
        if info["count"] > 30:
            problems.append(f"{skill}: count above 30")
        by_id = {p["id"]: p for p in thirty}
        for pid in info["posting_ids"]:
            if skill not in skills_in_text(by_id[pid]["description"]):
                problems.append(f"{skill}: {pid} does not mention it")

    independent_total = sum(len(skills_in_text(p["description"])) for p in thirty)
    counted_total = sum(i["count"] for i in counts.values())
    if independent_total != counted_total:
        problems.append("total skill mentions differ from an independent recount")

    top = ", ".join(f"{s}={i['count']}" for s, i in list(counts.items())[:5])
    sample = next(iter(counts.items()))
    evidence = (
        f"{len(counts)} skills counted; top 5: {top}. "
        f"Every count equals its number of posting IDs; independent recount total = {independent_total}. "
        f"Example: {sample[0]} appears in {sample[1]['posting_ids'][:4]}..."
    )
    record(
        "TC1", "30 Data Analyst postings",
        "skill frequencies with posting count per skill",
        f"{len(thirty)} postings analysed, {len(counts)} skills, each with a posting count and IDs",
        evidence, problems,
    )


def tc2():
    raw = load_postings("data/postings.json")
    unique = dedup(raw)
    deduped = count_skills(unique)
    naive = count_skills(raw)
    problems = []

    first = raw[0]
    key = make_dedup_key(first)
    group = [p["id"] for p in raw if make_dedup_key(p) == key]
    kept = [p["id"] for p in unique if p["id"] in group]

    if len(group) != 3:
        problems.append(f"expected 3 copies of the job, found {len(group)}")
    if kept != [group[0]]:
        problems.append(f"kept {kept}, expected only {group[0]}")

    counted_ids = {pid for i in deduped.values() for pid in i["posting_ids"]}
    extra = [g for g in group[1:] if g in counted_ids]
    if extra:
        problems.append(f"duplicate IDs were counted: {extra}")

    first_skills = skills_in_text(first["description"])
    if not first_skills:
        problems.append("the repeated job has no skills, so the test proves nothing")
    for s in first_skills:
        diff = naive[s]["count"] - deduped[s]["count"]
        if diff != 2:
            problems.append(f"{s}: without dedup the count is only {diff} higher, expected 2")

    s0 = sorted(first_skills)[0] if first_skills else "-"
    evidence = (
        f"Copies {group} share one key; kept {kept}. "
        f"{len(raw)} raw -> {len(unique)} unique. "
        f"{s0}: {naive[s0]['count'] if s0 in naive else '-'} without dedup, "
        f"{deduped[s0]['count'] if s0 in deduped else '-'} with dedup."
    )
    record(
        "TC2", "Same posting syndicated on 3 sites",
        "counted once",
        f"3 copies {group} counted once; {len(raw)} raw -> {len(unique)} unique",
        evidence, problems,
    )


def tc3():
    with open(RESUME_PATH, encoding="utf-8") as f:
        resume_before = f.read()
    hash_before = file_hash(RESUME_PATH)

    unique = dedup(load_postings("data/postings.json"))
    counts = count_skills(unique)
    gaps = find_gaps(resume_before, counts)
    by_skill = {g["skill"]: g for g in gaps}
    problems = []

    sql = by_skill.get("SQL")
    excel = by_skill.get("Excel")
    if sql is None:
        problems.append("SQL does not appear in the postings")
    elif sql["status"] != "gap":
        problems.append(f"SQL status is {sql['status']}, expected gap")
    if excel is None or excel["status"] != "covered":
        problems.append("Excel should be covered")

    expected_covered = skills_in_text(resume_before) & set(counts)
    covered = {g["skill"] for g in gaps if g["status"] == "covered"}
    if covered != expected_covered:
        problems.append(f"covered {sorted(covered)} but resume only mentions {sorted(expected_covered)}")

    with open(RESUME_PATH, encoding="utf-8") as f:
        resume_after = f.read()
    if resume_after != resume_before or file_hash(RESUME_PATH) != hash_before:
        problems.append("the resume was modified")

    evidence = (
        f"SQL asked for in {counts['SQL']['count'] if 'SQL' in counts else 0} postings, "
        f"status={sql['status'] if sql else '-'}. "
        f"Excel evidence: '{excel['evidence'] if excel else '-'}'. "
        f"Resume hash before/after identical: {hash_before == file_hash(RESUME_PATH)}."
    )
    record(
        "TC3", "Resume mentions only Excel",
        "SQL marked as a gap; no skill added to the resume",
        f"SQL={sql['status'] if sql else 'missing'}; Excel={excel['status'] if excel else 'missing'}; resume unchanged={resume_after == resume_before}",
        evidence, problems,
    )


def tc4():
    with open(RESUME_PATH, encoding="utf-8") as f:
        resume = f.read()
    few = load_postings("data/postings_few.json")
    res = analyze(few, resume)
    problems = []

    if res["status"] != "needs_confirmation":
        problems.append(f"status is {res['status']}, expected needs_confirmation")
    if "skill_counts" in res or "gaps" in res:
        problems.append("analysis ran even though evidence was too thin")
    if res.get("postings_found") != len(few):
        problems.append("the posting set was changed (widened)")
    for option in ("widen_city", "widen_role"):
        if option not in res.get("options", []):
            problems.append(f"missing option {option}")
    if "widen" not in res.get("message", "").lower():
        problems.append("message does not ask about widening")

    evidence = (
        f"{len(few)} postings found (below the minimum of 5). "
        f"Status={res['status']}. Options={res.get('options')}. "
        f"Message: {res.get('message', '')[:120]}"
    )
    record(
        "TC4", "Fewer than 5 postings found",
        "asks before widening city or role",
        f"stopped with status {res['status']} after {len(few)} postings; offered {res.get('options')}",
        evidence, problems,
    )


def write_report():
    lines = ["# Test report", ""]
    for r in RESULTS:
        lines += [
            f"## {r['test_case']}: {r['scenario']}",
            f"- **Result:** {'PASS' if r['passed'] else 'FAIL'}",
            f"- **Expected:** {r['expected']}",
            f"- **Actual:** {r['actual']}",
            f"- **Evidence:** {r['evidence']}",
            "",
        ]
    with open("test_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    init_db()
    for test in (tc1, tc2, tc3, tc4):
        test()

    for r in RESULTS:
        print(f"{r['test_case']}  {'PASS' if r['passed'] else 'FAIL'}  {r['scenario']}")
        print(f"      expected: {r['expected']}")
        print(f"      actual:   {r['actual']}")
        print(f"      evidence: {r['evidence']}\n")

    write_report()
    passed = sum(r["passed"] for r in RESULTS)
    print(f"{passed}/{len(RESULTS)} passed. Report written to test_report.md")
    sys.exit(0 if passed == len(RESULTS) else 1)