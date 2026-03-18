"""
AssamStudentHub — Server
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

def load(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path): return []
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

@app.route("/api/jobs")
def api_jobs(): return jsonify(load("jobs.json"))

@app.route("/api/notifications")
def api_notifications(): return jsonify(load("notifications.json"))

@app.route("/api/exams")
def api_exams(): return jsonify(load("exams.json"))

@app.route("/api/status")
def api_status():
    return jsonify({
        "jobs":          len(load("jobs.json")),
        "notifications": len(load("notifications.json")),
        "exams":         len(load("exams.json")),
        "ready":         True,
    })

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    try:
        subprocess.Popen([sys.executable, os.path.join(HERE,"scraper.py")])
        return jsonify({"status":"started","message":"Scraper running — refresh in ~60 seconds."})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route("/")
def index():
    if not os.path.exists(INDEX): abort(404)
    return send_file(INDEX)

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print("\n" + "="*48)
    print("  AssamStudentHub")
    print("  http://localhost:5000")
    print("  Ctrl+C to stop")
    print("="*48 + "\n")
    app.run(debug=True, port=5000)
