"""
AssamStudentHub — Server
Reads from Supabase. Falls back to local JSON if Supabase unavailable.
Run:  python server.py
Open: http://localhost:5000
"""
from flask import Flask, jsonify, send_file, abort
from flask_cors import CORS
import json, os, subprocess, sys

app     = Flask(__name__)
CORS(app)
HERE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
INDEX    = os.path.join(HERE, "index.html")

# ── Try to import Supabase db module ──────────────────────────
try:
    from db import fetch_jobs, fetch_notifications, fetch_exams
    SUPABASE_OK = True
    print("  ✓ Supabase connected")
except Exception as e:
    SUPABASE_OK = False
    print(f"  ✗ Supabase unavailable ({e}) — using local JSON fallback")

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    print(f"DEBUG: Looking for data at {path}") # Add this line
    if not os.path.exists(path): 
        print(f"DEBUG: File NOT FOUND at {path}") # Add this line
        return []
    try:
        with open(path, encoding="utf-8") as f: 
            data = json.load(f)
            print(f"DEBUG: Loaded {len(data)} items from {filename}") # Add this line
            return data
    except Exception as e: 
        print(f"DEBUG: Error loading {filename}: {e}") # Add this line
        return []

def get_jobs():
    if SUPABASE_OK:
        try: return fetch_jobs()
        except Exception: pass
    return load_json("jobs.json")

def get_notifications():
    if SUPABASE_OK:
        try: return fetch_notifications()
        except Exception: pass
    return load_json("notifications.json")

def get_exams():
    if SUPABASE_OK:
        try: return fetch_exams()
        except Exception: pass
    return load_json("exams.json")

# ── API ──────────────────────────────────────────────────────
@app.route("/api/jobs")
def api_jobs():
    return jsonify(get_jobs())

@app.route("/api/notifications")
def api_notifications():
    return jsonify(get_notifications())

@app.route("/api/exams")
def api_exams():
    return jsonify(get_exams())

@app.route("/api/status")
def api_status():
    j = get_jobs()
    n = get_notifications()
    e = get_exams()
    return jsonify({
        "supabase":      SUPABASE_OK,
        "jobs":          len(j),
        "notifications": len(n),
        "exams":         len(e),
        "ready":         len(j) > 0,
    })

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    try:
        subprocess.Popen([sys.executable, os.path.join(HERE, "scraper.py")])
        return jsonify({"status":"started","message":"Scraper running — refresh in ~60 seconds."})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# ── Frontend ─────────────────────────────────────────────────
@app.route("/")
def index():
    if not os.path.exists(INDEX): abort(404)
    return send_file(INDEX)

# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print("\n" + "="*48)
    print("  AssamStudentHub")
    print("  http://localhost:5000")
    print("  Ctrl+C to stop")
    print("="*48)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
