"""
app.py  —  OIL LEVEL HMI  (Flask)
Run:  python app.py
All data stored internally in memory (no JSON file).
"""
from flask import Flask, jsonify, render_template, request
from datetime import datetime
import threading
import time
from queue import Queue
import yaml
import threading
import os
import serial
import select
from logger import setup_loggers
import paho.mqtt.client as mqtt
import requests

import yaml
tech_log, prod_log = setup_loggers()

weiVal=0
serial_error=False
MAX_ALLOWED_JUMP = 3.0   # kg
TANK_MAX_KG = 500.0
last_weight = None
infeed_local_remote_change=False
infeed_mode_change=False
remote_stop=False
local_stop=False

with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)

port = CONFIG["serial"]["port"]
baudrate = CONFIG["serial"]["baudrate"]
timeout = CONFIG["serial"]["timeout"]
print(port, baudrate)


  
 


app = Flask(__name__)

infeed_timeout = CONFIG["infeed"]["filling_time"]



# ── Internal Data Structure ────────────────────────────────────────────────────
data = {
    "timestamp": datetime.utcnow().isoformat(),
    "product": "CHOCO PUF",
    "product_code": "OLS-001",
    "tank": {
        "weight_kg": 147.0,
        "tare_kg": 0.0,
        "level_pct": 32.8,
        "max_kg": 100,
        "density_kgl": 0.87,
        "hi_alarm": False,
        "lo_alarm": False,
        "hi_threshold_pct": 90,
        "lo_threshold_pct": 10
    },
    "infeed": {
        "mode": "MANUAL",
        "operation": "LOCAL",
        "running": False,
        "valve_open": False,
        "manual_vol_L": 20.0,
        "flow_rate_lpm": 0.0
    },
    "outfeed": {
        "mode": "MANUAL",
        "operation": "LOCAL",
        "running": False,
        "valve_open": False,
        "manual_vol_L": 12.35,
        "flow_rate_lpm": 0.0
    },
    "log": []
}


# ── Helper to read default volumes from HTML input values ─────────────────
def load_volume_defaults():
    import re
    in_val = None
    out_val = None
    path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        # regex for input id="in-vol" value="..."
        m1 = re.search(r'id="in-vol"[^>]*value="([0-9.]+)"', html)
        m2 = re.search(r'id="out-vol"[^>]*value="([0-9.]+)"', html)
        in_val = float(m1.group(1)) if m1 else None
        out_val = float(m2.group(1)) if m2 else None
    except Exception:
        pass
    # also try config file
    try:
        with open("config.yml") as f:
            cfg = yaml.safe_load(f)
        iv = cfg.get("infeed", {}).get("manual_vol_L")
        ov = cfg.get("outfeed", {}).get("manual_vol_L")
        if iv is not None:
            in_val = iv
        if ov is not None:
            out_val = ov
    except Exception:
        pass
    return in_val, out_val


# initialize manual volumes from HTML if possible
in_default, out_default = load_volume_defaults()
if in_default is not None:
    data["infeed"]["manual_vol_L"] = in_default
if out_default is not None:
    data["outfeed"]["manual_vol_L"] = out_default


def on_message_weight(client, userdata, msg):
     
    global weiVal,serial_error
    try:
        if(msg.payload.decode().startswith("#")):
            print("Error message received from MQTT:", msg.payload.decode())
            serial_error=True  # Default to 0 if error message received
            tech_log.error("Error message received from MQTT: %s", msg.payload.decode())
            time.sleep(10)  # Wait before retrying
        else:
            weiVal = float(msg.payload.decode())
            serial_error=False
         
    except ValueError:
        print("Received non-numeric weight value:", msg.payload.decode())
        tech_log.error("Received non-numeric weight value: %s", msg.payload.decode())
        weiVal = 0.0  # Default to 0 if parsing fails
        serial_error=True
     


client = mqtt.Client()
client.on_message = on_message_weight
client.connect("localhost",1883)
client.subscribe("serial/weight")
client.loop_start()   # non-blocking



# ───────────────────────────────── Oil Addition Logic ────────────────────────────────────────────────────────
def oil_add(now_weight ,required_weight):
    tech_log.info("Oil addition process started")
    # Simulate oil addition logic here
    start_time = time.time()
    done=False
    global infeed_timeout
    global remote_stop
    global local_stop
    global serial_error
    global infeed_mode_change
    global infeed_local_remote_change
    global weiVal
    intial_weight=now_weight

    infeed_local_remote_change=False
    local_stop=False
    remote_stop=False
    serial_error=False
    infeed_mode_change=False
    tech_log.info("Starting oil addition. Initial weight: %.2f kg, Required weight: %.2f kg", intial_weight, required_weight)
    print("Starting oil addition. Initial weight: %.2f kg, Required weight: %.2f kg", intial_weight, required_weight)
    infeed_open(True)
    while(not done):
        current_time = time.time()
        elapsed_time = current_time - start_time
         
        if elapsed_time > infeed_timeout:  # Simulate a 10-second oil addition process
            done=True
            tech_log.warning("Oil add timed out after %d seconds for initial %f reqested %f. Final val %f", infeed_timeout, intial_weight, required_weight,weiVal)
            print("Oil add timed out after %d seconds for required %f weight %f. now val %f", infeed_timeout, intial_weight, required_weight,weiVal)
            
            break
        elif weiVal >= required_weight+intial_weight:
            done=True
            tech_log.info("Required weight reached.start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            print("Required weight reached.start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)  
            infeed_open(False)  # Close the infeed valve
            infeed_run_state(False)  # Stop the infeed process
            break
        elif serial_error:
            done=True
            tech_log.error("Serial error detected during oil addition. Aborting process.")
            print("Serial error detected during oil addition. Aborting process.")
            break
        elif remote_stop:
            done=True
            tech_log.warning("Remote stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            print("Remote stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            break
        elif local_stop:
            done=True
            tech_log.warning("Local stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            print("Local stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            break
        elif infeed_mode_change:
            done=True
            tech_log.warning("Infeed mode change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            print("Infeed mode change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            break
        elif infeed_local_remote_change:
            done=True
            tech_log.warning("Infeed local/remote change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            print("Infeed local/remote change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, weiVal)
            break

     
            
    infeed_open(False)  # Close the infeed valve
    infeed_run_state(False)  # Stop the infeed process





    time.sleep(2)  # Simulating time taken for oil addition

# ── Background Timer for Auto-Updates ─────────────────────────────────────────
def update_tank_data():
    """Update and print tank variables every 1 second"""
    while True:
        time.sleep(1)
        tank = data["tank"]
        
        weight_kg = tank.get("weight_kg", 0)
        level_pct = tank.get("level_pct", 0)
        tare_kg = tank.get("tare_kg", 0)
        max_kg = tank.get("max_kg", 0)
        density_kgl = tank.get("density_kgl", 0.87)
        hi_alarm = tank.get("hi_alarm", False)
        lo_alarm = tank.get("lo_alarm", False)
        hi_threshold_pct = tank.get("hi_threshold_pct", 80)
        lo_threshold_pct = tank.get("lo_threshold_pct", 20)
        
        '''print(f"[AUTO] Tank Weight: {weight_kg} kg, Level: {level_pct}%")
        print(f"[AUTO] Max: {max_kg} kg, Tare: {tare_kg} kg, Density: {density_kgl} kg/L")
        print(f"[AUTO] HI Alarm: {hi_alarm}, LO Alarm: {lo_alarm}")
        print(f"[AUTO] HI Threshold: {hi_threshold_pct}%, LO Threshold: {lo_threshold_pct}%")'''


def do_other_work():
    """Simulate other background work every 5 seconds"""
    while True:
        global weiVal
        time.sleep(1)

        data["tank"]["weight_kg"] = weiVal
        
        # Calculate level percentage
        tank = data["tank"]
        net_weight = max(0, weiVal - tank["tare_kg"])
        max_net = tank["max_kg"] - tank["tare_kg"]
        if max_net > 0:
            level_pct = (net_weight / max_net) * 100
            tank["level_pct"] = round(level_pct, 1)
        else:
            tank["level_pct"] = 0.0
        
        # Update alarms
        tank["hi_alarm"] = tank["level_pct"] >= tank["hi_threshold_pct"]
        tank["lo_alarm"] = tank["level_pct"] <= tank["lo_threshold_pct"]
        
        # Update timestamp
        data["timestamp"] = datetime.utcnow().isoformat()
         


 
print("saa")
 

 
# Start background timer thread
timer_thread = threading.Thread(target=update_tank_data, daemon=True)
timer_thread.start()


other_work_thread = threading.Thread(target=do_other_work, daemon=True)
other_work_thread.start()


# ── routes ────────────────────────────────────────────────────────────────────
 
def infeed_run_state(state_Now):
    # Set infeed running state
    requests.post("http://localhost:5000/api/run", json={
        "side": "infeed",
        "state": state_Now
    })  
    
def infeed_open(state_Now):
    # Open infeed valve
    requests.post("http://localhost:5000/api/control", json={
        "side": "infeed",
        "action": "valve",
        "state": state_Now
    })


@app.post("/api/run")
def set_run():
    """External endpoint that sets the running state directly.
    Useful for resetting the run button when an external sequence completes.
    Body: {"side": "infeed"|"outfeed", "state": true|false}
    """
    global data
    cmd = request.get_json(silent=True) or {}
    side = cmd.get("side")
    state = cmd.get("state")
    if side in ("infeed", "outfeed") and isinstance(state, bool):
        data[side]["running"] = state
        data[side]["valve_open"] = state
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "invalid payload"}), 400


@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/data")
def get_data():
    return jsonify(data)

@app.post("/api/control")
def post_control():
    """UI sends button presses here; data updated internally."""
    global data,weiVal,now_weight,remote_stop,local_stop,infeed_mode_change,infeed_local_remote_change
    cmd = request.get_json(silent=True) or {}
    side = cmd.get("side")          # "infeed" | "outfeed"
    action = cmd.get("action")      # "mode" | "operation" | "run" | "apply" | "valve"
    #print(side, action, cmd)
    infeed_local_remote_change=True
    # Check interlock: if opposite side is LOCAL and RUNNING, block this side
    opposite_side = "outfeed" if side == "infeed" else "infeed"
    if side in ("infeed", "outfeed"):
        opposite = data[opposite_side]
        # If opposite side is in LOCAL operation and running, block this side's actions
        if opposite["operation"] == "LOCAL" and opposite["running"]:
            if action in ("mode", "operation", "run", "apply"):
                return jsonify({"ok": False, "error": f"{opposite_side.upper()} is running. Cannot control {side}"})

    # helper to print current combination
    def print_state(sid):
        s = data[sid]
        mode = s.get("mode","")
        op = s.get("operation","")
        run = s.get("running",False)
        tag = f"{sid} {mode.lower()} {op.lower()} {'start' if run else 'stop'}"
        print(tag)
    # capture previous state for logging
    prev = None
    if side in ("infeed","outfeed"):
        sprev = data[side]
        prev = {
            "mode": sprev.get("mode"),
            "operation": sprev.get("operation"),
            "running": sprev.get("running")
        }
    
    if side in ("infeed", "outfeed"):
        s = data[side]
        if action == "mode":
            s["mode"] = "MANUAL" if s["mode"] == "AUTO" else "AUTO"
            print_state(side)
        elif action == "operation":
            s["operation"] = "REMOTE" if s["operation"] == "LOCAL" else "LOCAL"
            print_state(side)
            if s["operation"] == "REMOTE":
                s["running"] = False
                s["valve_open"] = False
                start_button_state = True
                stop_button_state = False
                print(f"Raction : {action} - Start Button: {start_button_state}, Stop Button: {stop_button_state}")
        elif action == "run":
            if s["operation"] != "REMOTE":
                s["running"] = not s["running"]
                s["valve_open"] = s["running"]
                start_button_state = not s["running"]
                stop_button_state = s["running"]
                #print(f"Laction : {action} - Start Button: {start_button_state}, Stop Button: {stop_button_state}")
                print_state(side)
                

        elif action == "valve":
            # Independent valve control: set state directly
            valve_state = cmd.get("state")  # True (open) or False (close)
            #print(side,action,valve_state)
            if valve_state is not None:
                s["valve_open"] = valve_state
            #print(f"{side} valve set to: {s['valve_open']}")
        elif action == "apply":
            vol = float(cmd.get("vol", 0))
            print(f"Applying volume {vol} L to {side}")
            if vol > 0:
                s["manual_vol_L"] = vol
                # persist to config.yml
                try:
                    with open("config.yml") as f:
                        cfg = yaml.safe_load(f) or {}
                except Exception:
                    cfg = {}
                if side not in cfg:
                    cfg[side] = {}
                cfg[side]["manual_vol_L"] = vol
                with open("config.yml", "w") as f:
                    yaml.safe_dump(cfg, f)
                
    

    # record transition events based on prev state and new state
    def add_event(evt):
        data.setdefault("log", []).append({"ts": datetime.utcnow().isoformat() + "Z", "evt": evt})
    if prev is not None:
        snew = data[side]
        m0,op0,run0 = prev["mode"], prev["operation"], prev["running"]
        m1,op1,run1 = snew["mode"], snew["operation"], snew["running"]
        if m0!=m1 or op0!=op1 or run0!=run1:
            # determine which of the 8 cases applies
            label = f"{side.upper()} "
            label += m1.lower() + " "
            label += op1.lower() + " "
            label += "start" if run1 else "stop"
            # explicit prints
            if m1=="AUTO" and op1=="LOCAL":
                if run1:
                    print(f"{side} auto local start")
                else:
                    print(f"{side} auto local stop")
            elif m1=="AUTO" and op1=="REMOTE":
                if run1:
                    print(f"{side} auto remote start")
                else:
                    print(f"{side} auto remote stop")
            elif m1=="MANUAL" and op1=="LOCAL":
                if run1:
                    print(f"{side} manual local start")
                     
                    
                    oil_add(weiVal,  data["infeed"]["manual_vol_L"] )  # Example: add 50 kg of oil
                    print("Oil addition started manual")

                else:
                    print(f"{side} manual local stop")
            elif m1=="MANUAL" and op1=="REMOTE":
                if run1:
                    print(f"{side} manual remote start")
                else:
                    print(f"{side} manual remote stop")
            # still log generic event
            add_event(label)
    # Extract tank variables
    tank = data["tank"]
    weight_kg = tank.get("weight_kg", 0)
    level_pct = tank.get("level_pct", 0)
    tare_kg = tank.get("tare_kg", 0)
    max_kg = tank.get("max_kg", 0)
    density_kgl = tank.get("density_kgl", 0.87)
    hi_alarm = tank.get("hi_alarm", False)
    lo_alarm = tank.get("lo_alarm", False)
    hi_threshold_pct = tank.get("hi_threshold_pct", 80)
    lo_threshold_pct = tank.get("lo_threshold_pct", 20)
    
    # Update tank with values (you can modify these variables in your program)
     
    
    tank["weight_kg"] = weight_kg
    tank["level_pct"] = level_pct
    tank["tare_kg"] = tare_kg
    tank["max_kg"] = max_kg
    tank["density_kgl"] = density_kgl
    tank["hi_alarm"] = hi_alarm
    tank["lo_alarm"] = lo_alarm
    tank["hi_threshold_pct"] = hi_threshold_pct
    tank["lo_threshold_pct"] = lo_threshold_pct
    
    '''print(f"Tank Weight: {weight_kg} kg, Level: {level_pct}%")
    print(f"Max: {max_kg} kg, Tare: {tare_kg} kg, Density: {density_kgl} kg/L")
    print(f"HI Alarm: {hi_alarm}, LO Alarm: {lo_alarm}")
    print(f"HI Threshold: {hi_threshold_pct}%, LO Threshold: {lo_threshold_pct}%")'''
    
    return jsonify({"ok": True})

@app.delete("/api/log")
def del_log():
    global data
    data["log"] = []
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Suppress Flask/Werkzeug access logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print("  Open http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
    