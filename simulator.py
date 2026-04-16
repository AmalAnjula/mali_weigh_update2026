"""
simulator.py  —  DATA UPDATER  (runs independently at 1 Hz)
============================================================
Reads data.json, applies physics/PLC data, writes back.
Replace simulate_step() with your real PLC / Modbus read.

Run:  python simulator.py
Then separately:  python app.py
"""
import json, time, datetime, os, random

FILE = os.path.join(os.path.dirname(__file__), "data.json")

def read():
    with open(FILE) as f:
        return json.load(f)

def write(d):
    tmp = FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, FILE)

def log_event(d, msg):
    d["log"].insert(0, {
        "ts":     datetime.datetime.utcnow().isoformat() + "Z",
        "evt":    msg,
        "weight": round(d["tank"]["weight_kg"], 3),
        "level":  round(d["tank"]["level_pct"], 1)
    })
    d["log"] = d["log"][:300]

def simulate_step(d):
    tank    = d["tank"]
    infeed  = d["infeed"]
    outfeed = d["outfeed"]
    density = tank.get("density_kgl", 0.87)

    if infeed["running"] and infeed["mode"] == "AUTO":
        rate_kg = 0.25
        tank["weight_kg"] = min(tank["max_kg"] + tank["tare_kg"], tank["weight_kg"] + rate_kg)
        infeed["flow_rate_lpm"] = round(rate_kg / density * 60, 2)
    else:
        infeed["flow_rate_lpm"] = 0.0

    if outfeed["running"] and outfeed["mode"] == "AUTO":
        rate_kg = 0.18
        tank["weight_kg"] = max(tank["tare_kg"], tank["weight_kg"] - rate_kg)
        outfeed["flow_rate_lpm"] = round(rate_kg / density * 60, 2)
    else:
        outfeed["flow_rate_lpm"] = 0.0

    tank["weight_kg"] = round(tank["weight_kg"] + random.uniform(-0.005, 0.005), 3)

    net = max(0.0, tank["weight_kg"] - tank["tare_kg"])
    tank["level_pct"] = round(min(100.0, max(0.0, net / tank["max_kg"] * 100)), 2)

    was_hi, was_lo = tank["hi_alarm"], tank["lo_alarm"]
    tank["hi_alarm"] = tank["level_pct"] >= tank["hi_threshold_pct"]
    tank["lo_alarm"] = tank["level_pct"] <= tank["lo_threshold_pct"]

    if tank["hi_alarm"] and not was_hi:
        log_event(d, "⚠ HI LEVEL ALARM")
    if tank["lo_alarm"] and not was_lo:
        log_event(d, "⚠ LO LEVEL ALARM")

    d["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

def main():
    print("=" * 52)
    print("  OIL LEVEL DATA UPDATER — 1 Hz")
    print(f"  File: {FILE}")
    print("  Ctrl+C to stop")
    print("=" * 52)
    tick = 0
    while True:
        t0 = time.time()
        try:
            d = read()
            simulate_step(d)
            write(d)
            net = d["tank"]["weight_kg"] - d["tank"]["tare_kg"]
            print(
                f"\r  [{tick:6d}]  wt={net:7.2f}kg  lv={d['tank']['level_pct']:5.1f}%  "
                f"in={'RUN' if d['infeed']['running'] else 'STP'}  "
                f"out={'RUN' if d['outfeed']['running'] else 'STP'}  "
                f"HI={'▲' if d['tank']['hi_alarm'] else '-'}  "
                f"LO={'▼' if d['tank']['lo_alarm'] else '-'}   ",
                end="", flush=True
            )
        except Exception as e:
            print(f"\n  [ERR] {e}")
        tick += 1
        time.sleep(max(0, 1.0 - (time.time() - t0)))

if __name__ == "__main__":
    main()
