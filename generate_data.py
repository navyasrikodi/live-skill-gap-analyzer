import json
import random

random.seed(42)

COMPANIES = [
    "Zenith Analytics", "BlueRiver Tech", "Orchid Software", "Nimbus Labs",
    "Kestrel Systems", "Lumen Retail", "Atlas Logistics", "Pioneer Health",
    "Crestline Finance", "Vertex Mobility", "Harbor Insurance", "Solstice Energy",
    "Meridian Foods", "Quartz Media", "Falcon Telecom", "Ironwood Steel",
    "Willow Education", "Ember Games", "Summit Pharma", "Cobalt Banking",
    "Tidal Shipping", "Aurora Travel", "Granite Builders", "Pixel Commerce",
    "Sapphire Auto", "Redwood Textiles", "Nova Payments", "Cedar Hotels",
    "Maple Agritech", "Echo Telehealth",
]

TITLES = ["Data Analyst", "Junior Data Analyst", "Senior Data Analyst", "Data Analyst"]
SOURCES = ["JobSiteA", "JobSiteB", "JobSiteC"]
CITY = "Hyderabad"
BASE_URL = "http://127.0.0.1:5000/job/"

# Chance that a posting asks for each skill
SKILL_PROB = {
    "SQL": 0.9, "Excel": 0.75, "Python": 0.7, "Tableau": 0.4,
    "Power BI": 0.4, "Statistics": 0.35, "Data Visualization": 0.3,
    "ETL": 0.2, "R": 0.15, "Machine Learning": 0.15, "Looker": 0.1,
}

# Different ways the same skill can be written
WORDING = {
    "SQL": ["SQL", "SQL", "PostgreSQL", "MySQL"],
    "Excel": ["Excel", "Microsoft Excel"],
    "Power BI": ["Power BI", "PowerBI"],
}


def make_description(company, skills):
    names = [random.choice(WORDING.get(s, [s])) for s in skills]
    skill_text = ", ".join(names) if names else "strong analytical thinking"
    return (
        f"{company} is hiring a Data Analyst in {CITY}. "
        f"You will clean data, build reports and present insights to the business team. "
        f"Required skills: {skill_text}."
    )


postings = []
for i, company in enumerate(COMPANIES, start=1):
    skills = [s for s, p in SKILL_PROB.items() if random.random() < p]
    postings.append({
        "id": f"J{i:03d}",
        "title": TITLES[i % len(TITLES)],
        "company": company,
        "city": CITY,
        "source": SOURCES[i % len(SOURCES)],
        "url": f"{BASE_URL}J{i:03d}",
        "description": make_description(company, skills),
    })

# TC2: the first job is also posted on two other sites
first = postings[0]
for new_id, source in [("J031", "JobSiteB"), ("J032", "JobSiteC")]:
    copy = dict(first)
    copy["id"] = new_id
    copy["source"] = source
    copy["url"] = BASE_URL + new_id
    postings.append(copy)

# TC4: only 3 postings
few = postings[:3]

resume = (
    "Mechanical engineer with 3 years of experience in manufacturing.\n"
    "Skills: Excel, AutoCAD, SolidWorks.\n"
    "Built Excel reports to track daily production and machine downtime.\n"
)

with open("data/postings.json", "w", encoding="utf-8") as f:
    json.dump(postings, f, indent=2)
with open("data/postings_few.json", "w", encoding="utf-8") as f:
    json.dump(few, f, indent=2)
with open("data/resume_excel_only.txt", "w", encoding="utf-8") as f:
    f.write(resume)

unique = {(p["company"], p["title"], p["city"]) for p in postings}
sql_count = sum("SQL" in p["description"] for p in postings)
print(f"Wrote {len(postings)} postings ({len(unique)} unique) to data/postings.json")
print(f"Wrote {len(few)} postings to data/postings_few.json")
print(f"Postings with an SQL-type word: {sql_count}")