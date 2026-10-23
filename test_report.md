# Test report

## TC1: 30 Data Analyst postings
- **Result:** PASS
- **Expected:** skill frequencies with posting count per skill
- **Actual:** 30 postings analysed, 11 skills, each with a posting count and IDs
- **Evidence:** 11 skills counted; top 5: SQL=28, Python=20, Tableau=17, Excel=14, Power BI=12. Every count equals its number of posting IDs; independent recount total = 129. Example: SQL appears in ['J001', 'J002', 'J003', 'J004']...

## TC2: Same posting syndicated on 3 sites
- **Result:** PASS
- **Expected:** counted once
- **Actual:** 3 copies ['J001', 'J031', 'J032'] counted once; 32 raw -> 30 unique
- **Evidence:** Copies ['J001', 'J031', 'J032'] share one key; kept ['J001']. 32 raw -> 30 unique. ETL: 6 without dedup, 4 with dedup.

## TC3: Resume mentions only Excel
- **Result:** PASS
- **Expected:** SQL marked as a gap; no skill added to the resume
- **Actual:** SQL=gap; Excel=covered; resume unchanged=True
- **Evidence:** SQL asked for in 28 postings, status=gap. Excel evidence: 'Skills: Excel, AutoCAD, SolidWorks.'. Resume hash before/after identical: True.

## TC4: Fewer than 5 postings found
- **Result:** PASS
- **Expected:** asks before widening city or role
- **Actual:** stopped with status needs_confirmation after 3 postings; offered ['widen_city', 'widen_role', 'keep_as_is']
- **Evidence:** 3 postings found (below the minimum of 5). Status=needs_confirmation. Options=['widen_city', 'widen_role', 'keep_as_is']. Message: Only 3 unique posting(s) found for 'Data Analyst' in Hyderabad. That is fewer than 5, so the skill counts would be unrel
