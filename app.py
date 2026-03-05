"""
app.py  —  OIL LEVEL HMI  (Flask)
Run:  python app.py
UI polls /api/data every 1 second.
simulator.py writes data.json independently at 1 Hz.
"""
from flask import Flask, jsonify, render_template, request
import json, os

app  = Flask(__name__)
FILE = os.path.join(os.path.dirname(__file__), "data.json")

def read():
    with open(FILE) as f:
        return json.load(f)

def write(d):
    tmp = FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, FILE)

# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/data")
def get_data():
    return jsonify(read())

@app.post("/api/control")
def post_control():
    """UI sends button presses here; written to data.json so simulator reads them."""
    cmd = request.get_json(silent=True) or {}
    d   = read()
    side = cmd.get("side")          # "infeed" | "outfeed"
    action = cmd.get("action")      # "mode" | "operation" | "run" | "apply"

    if side in ("infeed", "outfeed"):
        s = d[side]
        if action == "mode":
            s["mode"] = "MANUAL" if s["mode"] == "AUTO" else "AUTO"
        elif action == "operation":
            s["operation"] = "REMOTE" if s["operation"] == "LOCAL" else "LOCAL"
            if s["operation"] == "REMOTE":
                s["running"] = False
                s["valve_open"] = False
        elif action == "run":
            if s["operation"] != "REMOTE":
                s["running"] = not s["running"]
                s["valve_open"] = s["running"]
        elif action == "apply":
            vol = float(cmd.get("vol", 0))
            if vol > 0:
                s["manual_vol_L"] = vol
                kg = vol * d["tank"].get("density_kgl", 0.87)
                if side == "infeed":
                    d["tank"]["weight_kg"] = min(
                        d["tank"]["max_kg"] + d["tank"]["tare_kg"],
                        d["tank"]["weight_kg"] + kg)
                else:
                    d["tank"]["weight_kg"] = max(
                        d["tank"]["tare_kg"],
                        d["tank"]["weight_kg"] - kg)
    write(d)
    return jsonify({"ok": True})

@app.delete("/api/log")
def del_log():
    d = read(); d["log"] = []; write(d)
    return jsonify({"ok": True})

if __name__ == "__main__":
    print("  Open http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
