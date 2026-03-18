"""
AssamStudentHub — Scraper
Sources:
  JOBS:
    1. AssamCareer.com      — WordPress blog, article scraping
    2. DailyAssamJob.in     — clean WordPress job portal
    3. APSC                 — apsc.nic.in/advt_2025.php
    4. SLPRB                — hardcoded (SSL issues)
    5. NHM Assam            — nhm.assam.gov.in
    6. AESRB                — hardcoded (React SPA)
    7. NCS Portal           — API attempt + fallback
  NOTIFICATIONS:
    8. Tezpur University    — tezu.ac.in
    9. Gauhati University   — gauhati.ac.in + Google Sites
   10. Bodoland University  — buniv.edu.in
   11. Mangaldai College    — mangaldaicollege.org
  EXAMS:
   12. AHSEC               — ahsec.assam.gov.in
   13. SEBA                — sebaonline.org
   14. APSC exam notices   — apsc.nic.in

Run:  python scraper.py
"""

import requests
from bs4 import BeautifulSoup
import json, os, re
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Paths ──────────────────────────────────────────────────
HERE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
os.makedirs(DATA_DIR, exist_ok=True)
TODAY    = datetime.today().strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch(url, verify=False, timeout=25):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=verify)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    ERROR: {e}")
        return None

def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()

def extract_date(text):
    """Try to pull a date string from text."""
    patterns = [
        r'(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})',
        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+(\d{4})',
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})',
    ]
    months = {'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
              'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            g = m.groups()
            try:
                if re.match(r'\d{2}', g[0]):
                    return f"{g[2]}-{g[1]}-{g[0]}"
                else:
                    mo = months.get(g[0][:3].lower()) or months.get(g[1][:3].lower())
                    yr = g[2] if len(g[2]) == 4 else g[0] if len(g[0]) == 4 else g[1]
                    day = g[1] if g[0].isalpha() else g[0]
                    return f"{yr}-{mo}-{day.zfill(2)}"
            except Exception:
                continue
    return ""

def classify_type(title):
    t = title.lower()
    if any(k in t for k in ["professor","lecturer","faculty","research fellow","jrf","university","college","school teacher"]):
        return "academic"
    if any(k in t for k in ["oil india","private","ltd","pvt","bank","insurance"]):
        return "private"
    return "govt"

def pick_icon(title):
    t = title.lower()
    if any(k in t for k in ["police","constable","si ","sub inspector"]): return "👮"
    if any(k in t for k in ["bank","sbi","rbi","nabard","idbi"]): return "🏦"
    if any(k in t for k in ["railway","rrb","rites","irctc"]): return "🚂"
    if any(k in t for k in ["army","rifle","military","defence","bro","drdo"]): return "🛡️"
    if any(k in t for k in ["professor","lecturer","faculty","teacher","research"]): return "🎓"
    if any(k in t for k in ["court","judge","judicial","law"]): return "⚖️"
    if any(k in t for k in ["health","nurse","doctor","nhm","medical","aiims","hospital"]): return "🏥"
    if any(k in t for k in ["engineer","technical","polytechnic","nit","iit","aesrb"]): return "⚙️"
    if any(k in t for k in ["oil","ongc","hpcl","bpcl","iocl","ntpc","nhpc"]): return "🛢️"
    if any(k in t for k in ["forest","wildlife","environment"]): return "🌳"
    return "🏛️"

def make_job(jid, title, org, jtype, location, salary, last_date,
             qual, vacancies, desc, full_desc, ad_url, source):
    return {
        "id": jid, "title": clean(title), "org": clean(org),
        "orgIcon": pick_icon(title), "type": jtype,
        "location": clean(location), "salary": clean(salary),
        "lastDate": last_date, "qualification": clean(qual),
        "vacancies": str(vacancies), "description": clean(desc),
        "fullDesc": full_desc, "adUrl": ad_url, "source": source,
    }


# ════════════════════════════════════════════════════════════
#  SOURCE 1 — AssamCareer.com
#  WordPress blog — articles listed on homepage + category pages
# ════════════════════════════════════════════════════════════
def scrape_assamcareer():
    """
    AssamCareer.com is a Blogger site.
    - Homepage: https://www.assamcareer.com/
    - Label pages: /search/label/Banking, /search/label/Govt+Job
    - No /page/N pagination — Blogger uses ?updated-max=... for older posts
    """
    print("\n  [1] AssamCareer.com — assamcareer.com")
    jobs = []
    seen = set()
    # Blogger label URLs that work on AssamCareer
    pages = [
        "https://www.assamcareer.com/",
        "https://www.assamcareer.com/search/label/Banking",
        "https://www.assamcareer.com/search/label/Govt+Job",
        "https://www.assamcareer.com/search/label/Private+Job",
        "https://www.assamcareer.com/search/label/Teaching+Job",
        "https://www.assamcareer.com/search/label/Defence",
        "https://www.assamcareer.com/search/label/Police",
        "https://www.assamcareer.com/search/label/Railway",
    ]
    JOB_KW = ["recruitment","vacancy","post","hiring","notification","advt",
              "assistant","officer","engineer","teacher","professor","constable",
              "inspector","driver","nurse","doctor","clerk","staff","manager","loco"]

    for page_url in pages:
        soup = fetch(page_url)
        if not soup: continue

        # Blogger uses h3.post-title or h2 with .post-title class
        posts = (soup.select(".post-title") or
                 soup.select("h3.post-title") or
                 soup.select("h2.post-title") or
                 soup.select(".entry-title") or
                 soup.select("h3 a") or
                 soup.select("h2 a"))

        for el in posts[:15]:
            a = el if el.name == "a" else el.find("a")
            if not a: continue
            title = clean(a.get_text())
            href  = a.get("href","")
            if not title or len(title) < 10 or title in seen: continue
            if not any(k in title.lower() for k in JOB_KW): continue
            seen.add(title)

            # Get excerpt from sibling/parent
            parent = el.parent or el
            excerpt_el = (parent.find("div", class_="post-body") or
                          parent.find("div", class_="entry-content") or
                          parent.find("p"))
            excerpt = clean(excerpt_el.get_text())[:300] if excerpt_el else ""
            last_date = extract_date(excerpt + " " + title) or ""

            # Try to extract org name from title
            org_m = re.match(r'^(.+?)\s+(?:Recruitment|Vacancy|Notification|Hiring|Advt)', title, re.IGNORECASE)
            org = clean(org_m.group(1)) if org_m else "Assam Govt / Other"

            jobs.append(make_job(
                jid       = f"ac-{len(jobs)+1}",
                title     = title,
                org       = org,
                jtype     = classify_type(title),
                location  = "Assam",
                salary    = "",
                last_date = last_date,
                qual      = "",
                vacancies = "",
                desc      = excerpt or f"{title}. See official notification for full details.",
                full_desc = ["Full details in the official notification — click the title to view.",
                             "Apply before the last date mentioned in the official advertisement.",
                             "Source: AssamCareer.com"],
                ad_url    = href,
                source    = "AssamCareer.com",
            ))
        if len(jobs) >= 40: break

    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 2 — DailyAssamJob.in
#  Clean WordPress job portal with good structure
# ════════════════════════════════════════════════════════════
def scrape_dailyassamjob():
    print("\n  [2] DailyAssamJob.in")
    jobs = []
    seen = set()
    # DailyAssamJob is a Blogger site — uses /search/label/ URLs
    pages = [
        "https://www.dailyassamjob.in/",
        "https://www.dailyassamjob.in/search/label/Assam%20Govt%20Job",
        "https://www.dailyassamjob.in/search/label/Private%20Job",
        "https://www.dailyassamjob.in/search/label/Bank%20Job",
        "https://www.dailyassamjob.in/search/label/Railway%20Job",
        "https://www.dailyassamjob.in/search/label/Defence%20Job",
        "https://www.dailyassamjob.in/search/label/Teaching%20Job",
        "https://www.dailyassamjob.in/search/label/Guwahati%20Job",
    ]
    for page_url in pages:
        soup = fetch(page_url)
        if not soup: continue

        # DailyAssamJob is Blogger — uses .post-title or h3.post-title
        posts = (soup.select(".post-title") or soup.select("h3.post-title") or
                 soup.select("h2.post-title") or soup.select(".entry-title") or
                 soup.select("h3 a") or soup.select("article"))
        for art in posts[:20]:
            a = art if art.name == "a" else (art.find("a") or art.select_one("a"))
            if not a: continue
            title = clean(a.get_text())
            href  = a.get("href","")
            if not title or len(title) < 10 or title in seen: continue
            seen.add(title)

            excerpt_el = art.select_one("p") or art.select_one(".entry-summary")
            excerpt = clean(excerpt_el.get_text())[:280] if excerpt_el else ""
            last_date = extract_date(excerpt) or ""

            # parse org from title pattern: "ORG Name Recruitment"
            org_m = re.match(r'^(.+?)\s+(?:Recruitment|Vacancy|Notification|Hiring)', title, re.IGNORECASE)
            org = clean(org_m.group(1)) if org_m else "Assam Govt / Other"

            jobs.append(make_job(
                jid       = f"daj-{len(jobs)+1}",
                title     = title,
                org       = org,
                jtype     = classify_type(title),
                location  = "Assam",
                salary    = "",
                last_date = last_date,
                qual      = "",
                vacancies = "",
                desc      = excerpt or f"{title}. Check official notification for details.",
                full_desc = ["Check official advertisement for full eligibility details.",
                             "Apply before last date on the official portal."],
                ad_url    = href,
                source    = "DailyAssamJob.in",
            ))

    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 3 — APSC (apsc.nic.in)
# ════════════════════════════════════════════════════════════
def scrape_apsc():
    print("\n  [3] APSC — apsc.nic.in")
    soup = fetch("https://apsc.nic.in/advt_2025.php")
    if not soup: return []

    link_map = {}
    for a in soup.find_all("a", href=True):
        txt  = clean(a.get_text())
        href = a["href"]
        if not href.startswith("http"):
            href = "https://apsc.nic.in/" + href.lstrip("/")
        if txt: link_map[txt[:80].upper()] = href

    text   = soup.get_text(" ")
    blocks = re.split(r'(?=ADVT\.?\s*NO\.?\s*\d+/\d{4})', text, flags=re.IGNORECASE)
    jobs   = []

    for block in blocks:
        m = re.match(r'ADVT\.?\s*NO\.?\s*(\d+/\d{4})\s+(.+?)(?=ADVT\.?\s*NO\.|\Z)',
                     block, re.IGNORECASE | re.DOTALL)
        if not m: continue
        advt_no = m.group(1).strip()
        raw     = clean(m.group(2))
        date_m  = re.search(r'APPLICATION START DATE[:\s]*([\d\-/]+)', raw, re.IGNORECASE)
        start   = date_m.group(1).replace("/","-") if date_m else ""
        title   = re.sub(r'\s*(APPLY HERE|APPLICATION START DATE.*)', '', raw, flags=re.IGNORECASE).strip()[:200]
        if not title or len(title) < 6: continue

        ad_url = "https://apsc.nic.in/advt_2025.php"
        for key, url in link_map.items():
            if advt_no.replace("/","") in key or advt_no in key:
                ad_url = url; break

        jobs.append(make_job(
            jid       = f"apsc-{advt_no.replace('/','_')}",
            title     = title,
            org       = "Assam Public Service Commission (APSC)",
            jtype     = classify_type(title),
            location  = "Assam",
            salary    = "As per 7th Pay Commission",
            last_date = "",
            qual      = "As per advertisement",
            vacancies = "",
            desc      = f"APSC Advt. No. {advt_no}: {title}.",
            full_desc = [f"Advertisement No: {advt_no}",
                         "Apply online at apsc.nic.in.",
                         "Check official PDF for eligibility, age limit and syllabus.",
                         f"Application start: {start or 'see official site'}"],
            ad_url    = ad_url,
            source    = "APSC Official",
        ))

    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 4 — SLPRB (hardcoded — SSL issues on their site)
# ════════════════════════════════════════════════════════════
SLPRB_DATA = [
    {"advt":"SLPRB/REC/CONST(AB&UB)/2025","title":"Constable (UB) & Constable (AB) — Assam Police","vacancies":"1715","salary":"₹14,000–₹70,000","qual":"Class 10 (AB) / Class 12 (UB)","lastDate":"2026-06-16","url":"https://apcap.in","desc":["1052 Constable (UB) + 663 Constable (AB) posts.","Age: 18–25 years as on 01-01-2026.","No application fee for any category.","Apply at apcap.in."]},
    {"advt":"SLPRB/REC/SI(UB)/2025","title":"Sub Inspector (UB), Station Officer, Squad Commander & Assistant Jailor","vacancies":"102","salary":"₹14,000–₹70,000","qual":"Graduation from recognised University","lastDate":"2026-06-16","url":"https://apcap.in","desc":["48 SI (UB) + 4 SI Communication + 6 Station Officer (F&ES).","5 Squad Commander + 39 Assistant Jailor.","Apply at apcap.in."]},
    {"advt":"SLPRB/REC/DRIVER/2025","title":"Driver Constable, Dispatch Rider & Driver (F&ES/Forest)","vacancies":"371","salary":"₹14,000–₹70,000","qual":"Class 10 + Valid Driving Licence","lastDate":"2026-06-16","url":"https://apcap.in","desc":["127 Driver Constable (Assam Police).","90 Driver + 4 Driver Operator (F&ES).","Valid driving licence mandatory.","Apply at apcap.in."]},
    {"advt":"SLPRB/REC/SAFAI/2025","title":"Safai Karmachari — Assam Police, Commando Battalions, F&ES & DGCD","vacancies":"112","salary":"₹12,000–₹52,000","qual":"Class 8 from recognised Board","lastDate":"2026-06-16","url":"https://apcap.in","desc":["96 posts in Assam Police + 3 Commando + 5 F&ES + 8 DGCD/CGHG.","Age: 18–40 years.","Apply at apcap.in."]},
    {"advt":"SLPRB/REC/FIREMAN/2025","title":"Fireman & Forest Guard — F&ES and Forest Department","vacancies":"200","salary":"₹14,000–₹60,500","qual":"Class 10 passed","lastDate":"2026-06-16","url":"https://apcap.in","desc":["Fireman posts in Fire & Emergency Services.","Forest Guard posts in Forest Department.","Physical test mandatory.","Apply at apcap.in."]},
]

def scrape_slprb():
    print("\n  [4] SLPRB — hardcoded (SSL issues)")
    jobs = [make_job(
        jid=f"slprb-{i+1}", title=n["title"],
        org="SLPRB Assam (Assam Police)", jtype="govt",
        location="Assam", salary=n["salary"],
        last_date=n["lastDate"], qual=n["qual"],
        vacancies=n["vacancies"],
        desc=f"SLPRB Notification {n['advt']}: {n['title']}.",
        full_desc=n["desc"], ad_url=n["url"],
        source="SLPRB Assam Official"
    ) for i, n in enumerate(SLPRB_DATA)]
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 5 — NHM Assam
# ════════════════════════════════════════════════════════════
# NHM Assam site consistently times out — hardcoded current notifications
# Update when new NHM recruitments are announced at nhm.assam.gov.in
NHM_DATA = [
    {"title":"Community Health Officer (CHO) Recruitment 2025–26","vacancies":"500+","salary":"₹25,000/month","qual":"B.Sc Nursing / GNM / BAMS / BHMS with bridge course","lastDate":"2026-08-30","desc":["500+ posts across rural health centres in Assam.","Contractual appointment renewable annually.","Apply at nhm.assam.gov.in.","Assam domicile required."]},
    {"title":"Staff Nurse (Contractual) Recruitment 2025–26","vacancies":"Multiple","salary":"₹18,000–₹22,000/month","qual":"GNM / B.Sc Nursing from recognised institution","lastDate":"2026-08-30","desc":["Posts in District Hospitals, CHCs and PHCs across Assam.","Contractual appointment under NHM.","Apply online at nhm.assam.gov.in."]},
    {"title":"Lab Technician & Radiographer (Contractual) 2025–26","vacancies":"Multiple","salary":"₹12,000–₹18,000/month","qual":"DMLT / B.Sc MLT / Diploma in Radiology","lastDate":"2026-08-30","desc":["Posts across District and Sub-District Hospitals.","Walk-in interview mode for some posts.","Check nhm.assam.gov.in for district-wise vacancies."]},
    {"title":"Auxiliary Nurse Midwife (ANM) Recruitment 2025–26","vacancies":"Multiple","salary":"₹11,000–₹13,000/month","qual":"ANM Certificate from recognised institution","lastDate":"2026-08-30","desc":["Sub-Centre and PHC level posts across rural Assam.","Priority to local candidates from respective districts.","Apply at nhm.assam.gov.in."]},
    {"title":"District Programme Manager & Block Programme Manager 2025","vacancies":"Multiple","salary":"₹30,000–₹45,000/month","qual":"MBA / MPH / MSW or equivalent PG degree","lastDate":"2026-07-31","desc":["Management positions under NHM district and block offices.","3–5 years experience in health sector preferred.","Apply at nhm.assam.gov.in."]},
    {"title":"ASHA Facilitator & Block Trainer Recruitment 2025","vacancies":"Multiple","salary":"₹10,000–₹12,000/month","qual":"Class 12 + experience in community health work","lastDate":"2026-09-30","desc":["Community-level positions across all districts.","Preference to female candidates from the community.","Apply via District NHM office."]},
]

def scrape_nhm():
    print("\n  [5] NHM Assam — nhm.assam.gov.in (site times out — using known posts)")
    jobs = [make_job(
        jid=f"nhm-{i+1}", title=n["title"],
        org="NHM Assam (National Health Mission)", jtype="govt",
        location="Assam", salary=n["salary"],
        last_date=n["lastDate"], qual=n["qual"], vacancies=n["vacancies"],
        desc=f"NHM Assam: {n['title']}.",
        full_desc=n["desc"],
        ad_url="https://nhm.assam.gov.in",
        source="NHM Assam Official"
    ) for i, n in enumerate(NHM_DATA)]
    print(f"    ✓ {len(jobs)} jobs (hardcoded — nhm.assam.gov.in times out)")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 6 — AESRB (hardcoded — React SPA)
# ════════════════════════════════════════════════════════════
AESRB_DATA = [
    {"advt":"AESRB-02/2025 & 03/2025","title":"Assistant Professor (Technical & Non-Technical) — State Engineering Colleges","vacancies":"58","salary":"₹57,700–₹1,82,400","qual":"B.E./B.Tech + M.E./M.Tech First Class","lastDate":"2026-05-08","url":"https://www.aesrb.in","desc":["58 vacancies in State Engineering Colleges.","Apply online at aesrb.in only.","Fee: ₹250 Gen / ₹150 OBC / Free SC/ST/PwBD.","Written Exam + Teaching Proficiency Test."]},
    {"advt":"AESRB-01/2025","title":"Lecturer & Senior Instructor — Government Polytechnic Institutes","vacancies":"343","salary":"₹30,000–₹1,10,000","qual":"B.E./B.Tech or Master's Degree First Class","lastDate":"2026-09-01","url":"https://www.aesrb.in","desc":["343 vacancies across Technical and Non-Technical disciplines.","Apply online at aesrb.in.","Fee: ₹250 Gen / ₹150 OBC / Free SC/ST."]},
]

def scrape_aesrb():
    print("\n  [6] AESRB — hardcoded (React SPA)")
    jobs = [make_job(
        jid=f"aesrb-{i+1}", title=n["title"],
        org="Assam Engineering Service Recruitment Board (AESRB)", jtype="academic",
        location="Assam", salary=n["salary"],
        last_date=n["lastDate"], qual=n["qual"], vacancies=n["vacancies"],
        desc=f"AESRB {n['advt']}: {n['title']}.",
        full_desc=n["desc"], ad_url=n["url"],
        source="AESRB Official"
    ) for i, n in enumerate(AESRB_DATA)]
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ════════════════════════════════════════════════════════════
#  SOURCE 7 — NCS Portal (API attempt + fallback)
# ════════════════════════════════════════════════════════════
def scrape_ncs():
    print("\n  [7] NCS Portal — ncs.gov.in")
    for api_url in ["https://www.ncs.gov.in/_vti_bin/NCS/JobSearch.svc/SearchJobs",
                    "https://www.ncs.gov.in/api/jobs/search"]:
        try:
            r = requests.post(api_url,
                json={"StateName":"Assam","PageIndex":1,"PageSize":20,"SortBy":"PostedDate","SortOrder":"DESC"},
                headers={**HEADERS,"Content-Type":"application/json"},
                timeout=15, verify=False)
            if r.status_code == 200:
                data  = r.json()
                items = (data.get("d",{}).get("Jobs") or data.get("Jobs") or data.get("data") or [])
                if items:
                    jobs = []
                    for item in items[:15]:
                        title = clean(item.get("JobTitle") or item.get("Title") or "")
                        if not title: continue
                        org  = clean(item.get("OrganizationName") or item.get("Employer") or "")
                        jid  = str(item.get("JobId") or item.get("Id") or len(jobs)+1)
                        jobs.append(make_job(
                            jid=f"ncs-{jid}", title=title, org=org or "NCS Portal Employer",
                            jtype=classify_type(title), location=clean(item.get("Location") or "Assam"),
                            salary=clean(item.get("SalaryRange") or ""),
                            last_date=(item.get("LastDate") or "")[:10],
                            qual=clean(item.get("Qualification") or ""), vacancies=str(item.get("Vacancy") or ""),
                            desc=f"{title} — {org}. Apply via NCS Portal.",
                            full_desc=["Apply at ncs.gov.in (free registration required).",
                                       "Includes govt, PSU and private jobs."],
                            ad_url=f"https://www.ncs.gov.in/job-seeker/Pages/JobDetail.aspx?JobId={jid}",
                            source="NCS Portal (ncs.gov.in)"
                        ))
                    print(f"    ✓ {len(jobs)} jobs via API")
                    return jobs
        except Exception:
            continue

    print("    API unavailable — adding browse card")
    return [make_job(
        jid="ncs-assam", title="Browse All Assam Jobs — NCS Portal",
        org="National Career Service Portal", jtype="govt",
        location="Assam", salary="Varies", last_date="", qual="Varies", vacancies="Multiple",
        desc="NCS portal lists hundreds of govt and private jobs in Assam, updated daily.",
        full_desc=["Register free at ncs.gov.in to apply.",
                   "Includes govt, PSU and private sector jobs.",
                   "Filter by district, qualification and salary range."],
        ad_url="https://www.ncs.gov.in/jobs-in-assam",
        source="NCS Portal (ncs.gov.in)"
    )]


# ════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ════════════════════════════════════════════════════════════
NOTIF_KW = {
    "admission":   ["admission","apply","application","enroll","merit list","allotment","counselling","seat","registration","fyugp","prospectus"],
    "exam":        ["exam","examination","result","routine","schedule","timetable","form fill","hall ticket","admit card","semester","backlog"],
    "recruitment": ["recruitment","vacancy","interview","faculty","professor","advt","advertisement","walk-in","staff","appointment"],
    "circular":    ["notice","circular","notification","tender","holiday","fee","affiliation","regarding","important","minutes","corrigendum"],
}

def classify_notif(title):
    t = title.lower()
    for cat, kws in NOTIF_KW.items():
        if any(k in t for k in kws): return cat
    return "circular"

def notif(uid, uni, label, icon, title, url, desc="", details=None, deadline=None):
    return {"id":uid, "uni":uni, "uniLabel":label, "icon":icon,
            "cat":classify_notif(title), "title":title,
            "date":TODAY, "deadline":deadline, "url":url,
            "description":desc, "details":details or []}

def _scrape_notif_links(soup, uni, label, icon, prefix, base_url, limit=20):
    if not soup: return []
    items, seen = [], set()
    for a in soup.select("a"):
        title = clean(a.get_text())
        href  = a.get("href","")
        if len(title) < 10 or title in seen: continue
        if not any(k in title.lower() for k in
                   list(NOTIF_KW["admission"]) + list(NOTIF_KW["exam"]) +
                   list(NOTIF_KW["recruitment"]) + ["notice","circular","result","schedule","routine"]):
            continue
        if any(s in title.lower() for s in ["home","sign in","sitemap","google","report abuse","about","contact","menu"]):
            continue
        seen.add(title)
        if href and not href.startswith("http"): href = base_url + href
        items.append(notif(f"{prefix}-{len(items)+1}", uni, label, icon, title, href or base_url))
        if len(items) >= limit: break
    return items

def scrape_tezpur_notifs():
    """
    Tezpur University notices live on tezu.ernet.in (not tezu.ac.in).
    Key pages:
      - /notice/noticeboard.html       — general notices
      - /notice/admission_2026.html    — admission notices
      - /notice/recruitment.html       — faculty/staff recruitment  (alias: /other/jobs.htm)
      - /ProjectWalkin/project_jobs.htm — project/JRF/SRF jobs
      - /notice/tender.html            — tenders
    """
    print("\n  [8] Tezpur University — tezu.ernet.in")
    items, seen = [], set()
    base = "https://www.tezu.ernet.in"

    pages = [
        (f"{base}/other/jobs.htm",                "recruitment"),
        (f"{base}/ProjectWalkin/project_jobs.htm","recruitment"),
        (f"{base}/notice/tender.html",            "circular"),
        (f"{base}/AwardsAchievements.html",       "circular"),
    ]

    for url, hint in pages:
        soup = fetch(url, verify=False)
        if not soup: continue
        # Tezpur uses <table> rows with <a> links — very classic govt site
        for a in soup.select("td a, li a, p a, a"):
            title = clean(a.get_text())
            href  = a.get("href","")
            if len(title) < 10 or title in seen: continue
            if any(s in title.lower() for s in ["home","contact","sitemap","privacy","about","accessibility","rti","terms"]):
                continue
            # Accept anything from these dedicated pages
            seen.add(title)
            if href and not href.startswith("http"):
                href = base + "/" + href.lstrip("/")
            items.append(notif(f"tez-{len(items)+1}", "tezpur", "Tezpur University",
                               "🔬", title, href or base))
            if len(items) >= 30: break
        if len(items) >= 30: break

    print(f"    ✓ {len(items)} notices")
    return items

def scrape_gauhati_notifs():
    print("\n  [9] Gauhati University — gauhati.ac.in")
    items, seen = [], set()
    for url in ["https://gauhati.ac.in/",
                "https://sites.google.com/a/gauhati.ac.in/notifications/notifications/general",
                "https://sites.google.com/a/gauhati.ac.in/notifications/examination",
                "https://sites.google.com/a/gauhati.ac.in/notifications/recruitment/recruitment"]:
        soup = fetch(url)
        if not soup: continue
        for a in soup.select("li a, td a, a"):
            title = clean(a.get_text())
            href  = a.get("href","")
            if len(title) < 15 or title in seen: continue
            if any(s in title.lower() for s in ["home","sign in","sitemap","google","report abuse"]): continue
            if not any(k in title.lower() for k in
                       list(NOTIF_KW["admission"]) + list(NOTIF_KW["exam"]) +
                       list(NOTIF_KW["recruitment"]) + ["notice","circular"]):
                continue
            seen.add(title)
            if href and not href.startswith("http"): href = "https://gauhati.ac.in" + href
            items.append(notif(f"gu-{len(items)+1}", "gauhati", "Gauhati University", "🏛️", title, href or "https://gauhati.ac.in"))
            if len(items) >= 25: break
        if len(items) >= 25: break
    print(f"    ✓ {len(items)} notices")
    return items

def scrape_bodoland_notifs():
    print("\n  [10] Bodoland University — buniv.edu.in")
    soup = None
    for url in ["https://www.buniv.edu.in/","http://www.buniv.edu.in/"]:
        soup = fetch(url, verify=False)
        if soup: break
    items = _scrape_notif_links(soup, "bodoland", "Bodoland University", "🌿", "bu", "https://www.buniv.edu.in", 15)
    print(f"    ✓ {len(items)} notices")
    return items

def scrape_mangaldai_notifs():
    print("\n  [11] Mangaldai College — mangaldaicollege.org")
    soup = fetch("https://mangaldaicollege.org/allNoticeView.php")
    if not soup: soup = fetch("https://mangaldaicollege.org/")
    items = _scrape_notif_links(soup, "mangaldai", "Mangaldai College", "🏫", "mc", "https://mangaldaicollege.org/", 15)
    print(f"    ✓ {len(items)} notices")
    return items


# ════════════════════════════════════════════════════════════
#  EXAMS
# ════════════════════════════════════════════════════════════
def classify_exam(title):
    t = title.lower()
    if any(k in t for k in ["hslc","class 10","class x","seba","madhyamik","ahsec","hs ","class 12","class xii","higher secondary"]): return "board"
    if any(k in t for k in ["semester","tdc","fyugp","university exam","end-semester","annual exam"]): return "university"
    if any(k in t for k in ["apsc","adre","direct recruitment","slprb exam","combined competitive","grade iii","grade iv"]): return "competitive"
    return "entrance"

def scrape_ahsec_exams():
    print("\n  [12] AHSEC — ahsec.assam.gov.in")
    soup = fetch("https://ahsec.assam.gov.in/")
    if not soup: return []
    items, seen = [], set()
    for a in soup.select("a"):
        title = clean(a.get_text())
        href  = a.get("href","")
        if len(title) < 10 or title in seen: continue
        if not any(k in title.lower() for k in ["exam","examination","routine","schedule","result","notification","admit","date","hs","higher secondary","ahsec"]): continue
        if any(s in title.lower() for s in ["home","about","contact","login","news"]): continue
        seen.add(title)
        if href and not href.startswith("http"): href = "https://ahsec.assam.gov.in" + href
        items.append({
            "id": f"ahsec-{len(items)+1}",
            "title": title,
            "cat": "board",
            "org": "Assam Higher Secondary Education Council (AHSEC)",
            "icon": "📝",
            "streams": "Arts / Science / Commerce",
            "examDate": "",
            "formDate": TODAY,
            "status": "upcoming",
            "url": href or "https://ahsec.assam.gov.in",
            "desc": f"AHSEC notification: {title}",
            "bullets": ["Check ahsec.assam.gov.in for full schedule.",
                        "Admit cards issued via respective colleges."],
            "source": "AHSEC Official",
        })
        if len(items) >= 10: break
    print(f"    ✓ {len(items)} exam notices")
    return items

def scrape_seba_exams():
    """
    sebaonline.org is JavaScript-rendered — returns empty HTML.
    We use hardcoded current SEBA notifications instead.
    Update this list when new SEBA notices are published.
    """
    print("\n  [13] SEBA — sebaonline.org (JS-rendered, using known notices)")
    SEBA_KNOWN = [
        {"title":"HSLC Annual Examination 2026 — Routine Released","url":"https://sebaonline.org","desc":"SEBA HSLC (Class 10) Annual Examination 2026 routine released. Exam begins February 2026.","bullets":["Exam: February–March 2026.","Admit cards distributed via school.","Results at sebaonline.org and resassam.nic.in."]},
        {"title":"HSLC 2026 — Form Fill-Up Notification","url":"https://sebaonline.org","desc":"SEBA announces form fill-up schedule for HSLC Annual Examination 2026 candidates.","bullets":["Form fill-up via school examination cell.","Regular, Ex-Regular and Compartmental candidates.","Check school notice board for deadline."]},
        {"title":"HSLC 2025 Result — Published at sebaonline.org","url":"https://sebaonline.org/result","desc":"SEBA HSLC 2025 Annual Examination results published online.","bullets":["Check results at sebaonline.org.","Results also via SMS on registered mobile.","Marksheet from school after official declaration."]},
        {"title":"HSLC 2026 Admit Card Download — Notice","url":"https://sebaonline.org","desc":"SEBA HSLC 2026 admit card download notice for regular and ex-regular candidates.","bullets":["Admit cards downloadable through school login.","Physical copies distributed by school.","Report any discrepancy to school immediately."]},
        {"title":"Class IX Annual Examination 2026 — Guidelines","url":"https://sebaonline.org","desc":"SEBA guidelines for Class IX Annual Examination conducted by affiliated schools.","bullets":["Conducted by individual schools under SEBA norms.","Results determine eligibility for Class X board exam.","Check school notice board for schedule."]},
    ]
    items = []
    for i, n in enumerate(SEBA_KNOWN):
        items.append({
            "id": f"seba-{i+1}",
            "title": n["title"],
            "cat": "board",
            "org": "Board of Secondary Education, Assam (SEBA)",
            "icon": "📝",
            "streams": "HSLC (Class 10) — All subjects",
            "examDate": "",
            "formDate": TODAY,
            "status": "upcoming",
            "url": n["url"],
            "desc": n["desc"],
            "bullets": n["bullets"],
            "source": "SEBA Official",
        })
    print(f"    ✓ {len(items)} exam notices (hardcoded — sebaonline.org is JS-rendered)")
    return items

def scrape_apsc_exams():
    print("\n  [14] APSC exam notices — apsc.nic.in")
    # APSC exam notices live on main page and advt pages
    soup = fetch("https://apsc.nic.in/")
    if not soup:
        soup = fetch("https://apsc.nic.in/advt_2025.php")
    if not soup: return []
    items, seen = [], set()
    for a in soup.select("a"):
        title = clean(a.get_text())
        href  = a.get("href","")
        if len(title) < 10 or title in seen: continue
        if not any(k in title.lower() for k in ["exam","examination","schedule","written test","date","cce","combined","interview"]): continue
        if any(s in title.lower() for s in ["home","about","career","apply now","advt"]): continue
        seen.add(title)
        if href and not href.startswith("http"): href = "https://apsc.nic.in/" + href.lstrip("/")
        items.append({
            "id": f"apsc-exam-{len(items)+1}",
            "title": title,
            "cat": "competitive",
            "org": "Assam Public Service Commission (APSC)",
            "icon": "🏆",
            "streams": "Civil Services / Engineering / Other posts",
            "examDate": "",
            "formDate": TODAY,
            "status": "upcoming",
            "url": href or "https://apsc.nic.in",
            "desc": f"APSC exam notice: {title}",
            "bullets": ["Check apsc.nic.in for full schedule.",
                        "Admit cards downloadable from official APSC portal."],
            "source": "APSC Official",
        })
        if len(items) >= 10: break
    print(f"    ✓ {len(items)} exam notices")
    return items


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def run():
    print("=" * 58)
    print("  AssamStudentHub — Scraper")
    print(f"  {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print("=" * 58)

    # ── JOBS ──────────────────────────────────────────────
    print("\n── JOBS ──────────────────────────────────────────────")
    all_jobs = []
    all_jobs += scrape_assamcareer()
    all_jobs += scrape_dailyassamjob()
    all_jobs += scrape_apsc()
    all_jobs += scrape_slprb()
    all_jobs += scrape_nhm()
    all_jobs += scrape_aesrb()
    all_jobs += scrape_ncs()

    # deduplicate by title similarity
    seen_titles = set()
    deduped = []
    for j in all_jobs:
        key = re.sub(r'\W+','',j['title'].lower())[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(j)
    all_jobs = deduped

    for i, j in enumerate(all_jobs, 1):
        j["id"] = i

    with open(os.path.join(DATA_DIR,"jobs.json"),"w",encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ {len(all_jobs)} jobs → data/jobs.json")

    # ── NOTIFICATIONS ──────────────────────────────────────
    print("\n── NOTIFICATIONS ─────────────────────────────────────")
    all_notifs = []
    all_notifs += scrape_tezpur_notifs()
    all_notifs += scrape_gauhati_notifs()
    all_notifs += scrape_bodoland_notifs()
    all_notifs += scrape_mangaldai_notifs()

    with open(os.path.join(DATA_DIR,"notifications.json"),"w",encoding="utf-8") as f:
        json.dump(all_notifs, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {len(all_notifs)} notifications → data/notifications.json")

    # ── EXAMS ──────────────────────────────────────────────
    print("\n── EXAMS ─────────────────────────────────────────────")
    all_exams = []
    all_exams += scrape_ahsec_exams()
    all_exams += scrape_seba_exams()
    all_exams += scrape_apsc_exams()

    with open(os.path.join(DATA_DIR,"exams.json"),"w",encoding="utf-8") as f:
        json.dump(all_exams, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {len(all_exams)} exam notices → data/exams.json")

    print("\n" + "=" * 58)
    print(f"  Total: {len(all_jobs)} jobs | {len(all_notifs)} notifications | {len(all_exams)} exams")
    print("  Run:  python server.py")
    print("  Open: http://localhost:5000")
    print("=" * 58 + "\n")

if __name__ == "__main__":
    run()
