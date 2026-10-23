import requests

CANDIDATES = [
    "https://help.tableau.com/current/guides/get-started-tutorial/en-us/get-started-tutorial-home.htm",
    "https://public.tableau.com/app/learn/how-to-videos",
    "https://www.tableau.com/learn/training",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (SkillGapAnalyzer demo)"}

for url in CANDIDATES:
    try:
        status = requests.get(url, headers=HEADERS, timeout=10).status_code
    except requests.RequestException as e:
        status = f"error: {type(e).__name__}"
    print(status, url)