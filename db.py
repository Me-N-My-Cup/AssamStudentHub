"""
AssamStudentHub — Supabase client
Compatible with supabase-py 2.9.x
"""
import os

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://iumuegzyjikowymusfnb.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1bXVlZ3p5amlrb3d5bXVzZm5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNzM2NTcsImV4cCI6MjA4NDk0OTY1N30.0Z8nPDP0LN10-wj2ni1aGM8WQtWl6v9cazATmWHe12E"
)

_client = None

def get_client():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client



def upsert_jobs(jobs: list) -> int:
    if not jobs: return 0
    sb = get_client()
    rows = [{
        "id":            str(j.get("id", "")),
        "title":         j.get("title", ""),
        "org":           j.get("org", ""),
        "org_icon":      j.get("orgIcon", ""),
        "type":          j.get("type", "govt"),
        "location":      j.get("location", ""),
        "salary":        j.get("salary", ""),
        "last_date":     j.get("lastDate") or None,
        "qualification": j.get("qualification", ""),
        "vacancies":     j.get("vacancies", ""),
        "description":   j.get("description", ""),
        "full_desc":     j.get("fullDesc", []),
        "ad_url":        j.get("adUrl", ""),
        "source":        j.get("source", ""),
    } for j in jobs]
    for i in range(0, len(rows), 100):
        sb.table("jobs").upsert(rows[i:i+100]).execute()
    return len(rows)


def upsert_notifications(notifs: list) -> int:
    if not notifs: return 0
    sb = get_client()
    rows = [{
        "id":          str(n.get("id", "")),
        "uni":         n.get("uni", ""),
        "uni_label":   n.get("uniLabel", ""),
        "icon":        n.get("icon", ""),
        "cat":         n.get("cat", "circular"),
        "title":       n.get("title", ""),
        "date":        n.get("date") or None,
        "deadline":    n.get("deadline") or None,
        "url":         n.get("url", ""),
        "description": n.get("description", ""),
        "details":     n.get("details", []),
    } for n in notifs]
    for i in range(0, len(rows), 100):
        sb.table("notifications").upsert(rows[i:i+100]).execute()
    return len(rows)


def upsert_exams(exams: list) -> int:
    if not exams: return 0
    sb = get_client()
    rows = [{
        "id":          str(e.get("id", "")),
        "title":       e.get("title", ""),
        "cat":         e.get("cat", "entrance"),
        "org":         e.get("org", ""),
        "icon":        e.get("icon", ""),
        "streams":     e.get("streams", ""),
        "exam_date":   e.get("examDate") or None,
        "form_date":   e.get("formDate") or None,
        "status":      e.get("status", "upcoming"),
        "url":         e.get("url", ""),
        "description": e.get("desc", ""),
        "bullets":     e.get("bullets", []),
        "source":      e.get("source", ""),
    } for e in exams]
    for i in range(0, len(rows), 100):
        sb.table("exams").upsert(rows[i:i+100]).execute()
    return len(rows)


# FETCH

def fetch_jobs() -> list:
    sb = get_client()
    res = sb.table("jobs").select("*").order("scraped_at", desc=True).limit(200).execute()
    return [{
        "id":            r["id"],
        "title":         r["title"],
        "org":           r["org"],
        "orgIcon":       r["org_icon"] or "🏛️",
        "type":          r["type"],
        "location":      r["location"],
        "salary":        r["salary"],
        "lastDate":      r["last_date"] or "",
        "qualification": r["qualification"],
        "vacancies":     r["vacancies"],
        "description":   r["description"],
        "fullDesc":      r["full_desc"] or [],
        "adUrl":         r["ad_url"],
        "source":        r["source"],
    } for r in (res.data or [])]


def fetch_notifications() -> list:
    sb = get_client()
    res = sb.table("notifications").select("*").order("scraped_at", desc=True).limit(300).execute()
    return [{
        "id":          r["id"],
        "uni":         r["uni"],
        "uniLabel":    r["uni_label"],
        "icon":        r["icon"] or "📋",
        "cat":         r["cat"],
        "title":       r["title"],
        "date":        r["date"] or "",
        "deadline":    r["deadline"],
        "url":         r["url"],
        "description": r["description"],
        "details":     r["details"] or [],
    } for r in (res.data or [])]


def fetch_exams() -> list:
    sb = get_client()
    res = sb.table("exams").select("*").order("exam_date").limit(100).execute()
    return [{
        "id":       r["id"],
        "title":    r["title"],
        "cat":      r["cat"],
        "org":      r["org"],
        "icon":     r["icon"] or "📝",
        "streams":  r["streams"],
        "examDate": r["exam_date"] or "",
        "formDate": r["form_date"] or "",
        "status":   r["status"],
        "url":      r["url"],
        "desc":     r["description"],
        "bullets":  r["bullets"] or [],
        "source":   r["source"],
    } for r in (res.data or [])]
