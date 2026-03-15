#!/usr/bin/env python3
"""
OLS Monitor — Flask Backend  +  MQTT Weight Thread
====================================================
Serves the HTML UI and handles all API calls.
A dedicated MQTT thread subscribes to the weight topic and pushes
the value (weiVal) straight into the shared state every message.

──────────────────────────────────────────────────────────────────
  MQTT CONFIG  (edit section below or set environment variables)
──────────────────────────────────────────────────────────────────
  MQTT_BROKER   broker hostname / IP   default: localhost
  MQTT_PORT     broker TCP port        default: 1883
  MQTT_TOPIC    weight topic           default: ols/weight
  MQTT_USER     username (optional)
  MQTT_PASS     password (optional)
──────────────────────────────────────────────────────────────────

Endpoints
---------
GET    /              -> index.html
GET    /api/data      -> full state JSON  (polled 1 Hz by UI)
POST   /api/control   -> button click events
POST   /api/update    -> push any state value  {"path":"tank.weight_kg","value":520}
POST   /api/buttons   -> enable/disable button {"button":"in-run-btn","disabled":true}
DELETE /api/log       -> clear event log

Terminal output for every button press:
  [BUTTON EVENT] {"side": "infeed", "button": "run", "value": "START", "state": true}

MQTT terminal output:
  [MQTT] Connected to localhost:1883
  [MQTT] weight = 523.40 kg  (level 52.34%)
  [MQTT] Error frame: #ERR_SERIAL
  [MQTT] Disconnected - reconnecting in 5 s
"""

import os, json, time, logging, logging.handlers, threading
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import yaml
from production_logger import ProductionLogger

import gpio_reader as gpio
 

inputs = {}


with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)

INFEED_TIMEOUT = CONFIG["infeed"]["filling_time"]
OUTFEED_TIMEOUT = CONFIG["outfeed"]["draining_time"]
print("INFEED_TIMEOUT =", INFEED_TIMEOUT, "seconds")
print("OUTFEED_TIMEOUT =", OUTFEED_TIMEOUT, "seconds")

   # seconds — max time allowed for one oil addition

 


# ── Try importing paho; warn clearly if missing ────────────────────
try:
    import paho.mqtt.client as mqtt_client
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("  paho-mqtt not installed - MQTT thread disabled.")
    print("   Install with:  pip install paho-mqtt")

# ══════════════════════════════════════════════════════════════════
#  MQTT CONFIGURATION  — edit here or override via env vars
# ══════════════════════════════════════════════════════════════════
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT",  "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC",  "serial/weight")
MQTT_USER   = os.getenv("MQTT_USER",   "")          # leave "" if no auth
MQTT_PASS   = os.getenv("MQTT_PASS",   "")

# ══════════════════════════════════════════════════════════════════
#  LOGGING  — all logs written to /logs/  (created if missing)
# ══════════════════════════════════════════════════════════════════
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


prod_logger = ProductionLogger(LOG_DIR)


_log_fmt     = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def _make_file_handler(filename: str, level=logging.DEBUG) -> logging.FileHandler:
    h = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        when="midnight",       # rotate every day at midnight
        backupCount=30,        # keep 30 days of logs
        encoding="utf-8",
    )
    h.setFormatter(_log_fmt)
    h.setLevel(level)
    return h

# Console handler — INFO and above, no werkzeug noise
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_fmt)
_console_handler.setLevel(logging.INFO)

# Root logger — sends everything to console + ols_app.log
logging.basicConfig(level=logging.DEBUG, handlers=[])   # clear default handlers
root_log = logging.getLogger()
root_log.setLevel(logging.DEBUG)
root_log.addHandler(_console_handler)
root_log.addHandler(_make_file_handler("ols_app.log"))

# Dedicated tech (MQTT / system) logger → also writes to ols_tech.log
tech_log = logging.getLogger("ols.tech")
tech_log.addHandler(_make_file_handler("ols_tech.log"))
tech_log.setLevel(logging.DEBUG)

# ── Silence Flask/Werkzeug access log lines ────────────────────────
# Suppresses:  192.168.x.x - - [..] "GET /api/data HTTP/1.1" 200 -
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("werkzeug").propagate = False


# ══════════════════════════════════════════════════════════════════
#  FLASK APP
# ══════════════════════════════════════════════════════════════════
app   = Flask(__name__, static_folder=".")
_lock = threading.Lock()

# ══════════════════════════════════════════════════════════════════
#  SHARED STATE  (all UI data lives here)
# ══════════════════════════════════════════════════════════════════
def _now():
    return datetime.now().isoformat(timespec="seconds")


state = {
    "product":      CONFIG.get("product", "Crude Oil"),
    "product_code": CONFIG.get("product_code", "OIL-001"),
    "timestamp":    _now(),

    "serial": {
        "port":     CONFIG.get("serial", {}).get("port",     "/dev/ttyUSB0"),
        "baudrate": CONFIG.get("serial", {}).get("baudrate", 9600),
    },

    "tank": {
        "weight_kg":         0.0,
        "tare_kg":           CONFIG["tank"].get("tare_kg", 0.0),
        "max_kg":            CONFIG["tank"].get("max_kg", 100.0),
        "level_pct":         0.0,
        "density_kgl":       CONFIG["tank"].get("density_kgl", 0.87),
        "infeed_valve":      CONFIG["tank"].get("infeed_valve", 5.0),
        "hi_threshold_pct":  CONFIG["tank"].get("hi_threshold_pct", 80),
        "lo_threshold_pct":  CONFIG["tank"].get("lo_threshold_pct", 20),
        "hi_level_kg":       CONFIG["tank"].get("hi_level_kg", 850.0),
        "lo_level_kg":       CONFIG["tank"].get("lo_level_kg", 10.0),
        "hi_alarm":          False,
        "lo_alarm":          False,
        "lo_level":          CONFIG["tank"].get("lo_level_kg", 20.0),
        "hi_level":          CONFIG["tank"].get("hi_level_kg", 85.0),
        

    },

# ── Physical sensor states ──────────────────────────────
    "sensors": {
        "lo_level": False,   # True = float switch triggered
        "hi_level": False,
    },

    "infeed": {
        "mode":         "AUTO",
        "operation":    "LOCAL",
        "running":      False,
        "valve_open":   False,
         "manual_vol_L": CONFIG["infeed"].get("manual_vol_L", 25.0),
         "auto_start_level": CONFIG["infeed"].get("auto_start_level", 60.0),
         
         

    },

    "outfeed": {
        "mode":         "AUTO",
        "operation":    "LOCAL",
        "running":      False,
        "valve_open":   False,
        "manual_vol_L": CONFIG["outfeed"].get("manual_vol_L", 26.0),
    },

    # ── MQTT status block — read by the UI ──────────────────────
    "mqtt": {
        "connected":    False,
        "serial_error": False,
        "last_value":   None,       # last raw value or error string
        "last_ts":      None,       # ISO timestamp of last good reading
        "topic":        MQTT_TOPIC,
        "broker":       f"{MQTT_BROKER}:{MQTT_PORT}",
    },

    "log": [],

    # ── UI button overrides (driven by /api/buttons) ─────────────
    "ui": {
        "buttons": {
            "in-mode-btn":  {"disabled": False},
            "in-op-btn":    {"disabled": False},
            "in-run-btn":   {"disabled": False},
            "out-mode-btn": {"disabled": False},
            "out-op-btn":   {"disabled": False},
            "out-run-btn":  {"disabled": False},
        }
    },
}

# ── Global MQTT value (also mirrored into state under lock) ────────
weiVal       = 0.0
serial_error = False
out_feed_sucess=False

 
# ── Infeed sequence control flags ──────────────────────────────────
# busyFlagInfeedBusy  → True while oil_add() sequence is running
# busyFlagOutfeedBusy → set True externally when outfeed is active;
#                       oil_add() will wait here before starting
busyFlagInfeedBusy  = False
busyFlagOutfeedBusy = False

# Interrupt flags — any of these being True aborts the oil_add loop
infeed_local_remote_change = False
infeed_mode_change         = False
infeed_remote_stop                = False
local_stop                 = False


low_level_sensor = False
hi_level_sensor=False
# ── Outfeed sequence control flags ─────────────────────────────────
outfeed_local_stop            = False
outfeed_remote_stop           = False
outfeed_local_remote_change   = False
outfeed_mode_change           = False


# ── GPIO HANDLER THREAD  (polls GPIO states and updates shared state) ───────────────────────

def gpio_handler():
    tech_log.info("GPIO handler thread started.")
    global inputs, local_stop, infeed_remote_stop,weiVal, low_level_sensor, infeed_mode_change, infeed_local_remote_change,outfeed_remote_stop
    global hi_level_sensor,out_feed_sucess
    gpio.update() 
    if gpio.state("intake_mode") and state["infeed"]["operation"] == "REMOTE" :
        state["infeed"]["mode"] = "AUTO"
    elif gpio.state("intake_mode") and state["infeed"]["operation"] == "MANUAL"  :
        state["infeed"]["mode"] = "MANUAL"



    if gpio.state("outk_remot") :
                if  not gpio.state("outk_remot"):
                    print("[GPIO] outfeed pin HIGH — setting outfeed mode to AUTO")
                    state["outfeed"]["mode"] = "AUTO"
                else:
                    print("[GPIO] outfeed pin LOW — setting outfeed mode to MANUAL")
                    state["outfeed"]["mode"] = "MANUAL"
    if gpio.state("intake_mode") :
                 
                if  not gpio.state("intake_mode"):
                    print("[GPIO] intake_mode_pin HIGH — setting infeed mode to AUTO")
                    state["infeed"]["mode"] = "AUTO"
                else:   
                    print("[GPIO] intake_mode_pin LOW — setting infeed mode to MANUAL")
                    state["infeed"]["mode"] = "MANUAL"


    while True:

        try:
            time.sleep(0.1)   # brief sleep to allow graceful shutdown (not implemented here, but good practice)
            gpio.update()  # read all GPIO pins and update internal state for edge detection
            

            # Rising edge — fires ONCE when button pressed, not every poll
            if gpio.rising("intke_start") and state["infeed"]["mode"]=="MANUAL" and state["infeed"]["operation"] == "REMOTE" and not state["infeed"]["running"]:
                    _now_w = weiVal
                    _req_w = state["infeed"]["manual_vol_L"]
                    t = threading.Thread(
                        target=oil_add,
                        args=(_now_w, _req_w,False),
                        daemon=True,
                        name="infeed_manual_remote",
                    )
                    t.start()
                    tech_log.info(
                        "oil_add thread started remote manual — now=%.2f kg  requested=%.2f kg",
                        _now_w, _req_w)
                    print(f"[infeed remote manual ] oil_add thread started  now={_now_w:.2f} kg  req={_req_w:.2f} kg")

            elif gpio.rising("intke_start") and state["infeed"]["mode"]=="AUTO" and state["infeed"]["operation"] == "REMOTE" and not state["infeed"]["running"]:
                    _now_w = weiVal
                    _req_w = state["infeed"]["manual_vol_L"]
                    t = threading.Thread(
                        target=auto_infeed_control,
                        args=(_now_w, _req_w,True),
                        daemon=True,
                        name="infeed_auto_remote",
                    )
                    t.start()
                    tech_log.info(
                        "oil_add thread started remote Auto — now=%.2f kg  requested=%.2f kg",
                        _now_w, _req_w)
                    print(f"[infeed remote auto ] oil_add thread started  now={_now_w:.2f} kg  req={_req_w:.2f} kg")
                
            if gpio.rising("intke_stop")  :
                tech_log.info("GPIO: intke_stop_pin triggered — setting remote_stop=True")
                print("[GPIO] intke_stop_pin triggered — setting remote_stop=True")
                infeed_remote_stop = True

            if gpio.rising("outtk_stop"):
                outfeed_remote_stop=True
                tech_log.info("GPIO: outtk_stop_pin triggered — setting outfeed_remote_stop=True")

            if gpio.rising("outtk_start") and state["outfeed"]["operation"]=="REMOTE":
                _req_vol = state["outfeed"]["manual_vol_L"]
                _req_vol = state["outfeed"]["manual_vol_L"]
                t = threading.Thread(
                        target=oil_drain,
                        args=(_req_vol,),
                        daemon=True,
                        name="outfeed_AUTO",
                    )
                t.start()
                tech_log.info("[outfeed] oil_drain thread REMOTE started — vol=%.2f L", _req_vol)
                print(f"[outfeed] oil_drain thread REMOTE started  vol={_req_vol:.2f} L")

            elif  not gpio.state("outtk_start") and state["outfeed"]["operation"]=="REMOTE" and state["outfeed"]["running"] and state["outfeed"]["mode"]=="AUTO" :
                time.sleep(1)
                print("stop wait")
                if not gpio.state("outtk_start") and state["outfeed"]["operation"]=="REMOTE":
                    out_feed_sucess=True
                    print("stop  actual wait")



                

            #if gpio.changed("intake_mode") and state["infeed"]["operation"] == "REMOTE":
            

            if gpio.changed("outk_remot") :
                if  not gpio.state("outk_remot"):
                    print("[GPIO] outfeed pin HIGH — setting outfeed mode to AUTO")
                    state["outfeed"]["mode"] = "AUTO"
                else:
                    print("[GPIO] outfeed pin LOW — setting outfeed mode to MANUAL")
                    state["outfeed"]["mode"] = "MANUAL"
            if gpio.changed("intake_mode") :
                 
                if  not gpio.state("intake_mode"):
                    print("[GPIO] intake_mode_pin HIGH — setting infeed mode to AUTO")
                    state["infeed"]["mode"] = "AUTO"
                else:   
                    print("[GPIO] intake_mode_pin LOW — setting infeed mode to MANUAL")
                    state["infeed"]["mode"] = "MANUAL"

                #tech_log.info("GPIO: intke_stop_pin triggered — setting local_stop=True")

  
                #tech_log.info("GPIO: intke_remot_pin triggered — setting remote_stop=True")
            state["sensors"]["lo_level"] =  gpio.state("lowr_sns")   # assuming active LOW sensor (0 when triggered)
            state["sensors"]["hi_level"] = gpio.state("up_sns")      # assuming active HIGH sensor (1 when triggered)
            low_level_sensor = not state["sensors"]["lo_level"] 
            hi_level_sensor =not state["sensors"]["hi_level"] 
             
 
            #print("tank low level sensor:", inputs["lowr_sns"], "  tank up level sensor:", inputs["up_sns"])
                #tech_log.info("GPIO: lowr_sns_pin triggered — setting low_level_sensor=True")

            # For demonstration, we log the pin states. In a real application,
            # you would use these values to update the shared state or trigger actions.
             
        except Exception as e:
            tech_log.error(f"Error reading GPIO states: {e}")
        #time.sleep(1)   # poll interval


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def _log(event, **extras):
    """Append a log entry. Always snapshots current tank weight & level_pct
    so every row in the UI table has numbers to display."""
    tk = state["tank"]
    net_kg  = round(max(0.0, tk["weight_kg"] - tk.get("tare_kg", 0.0)), 2)
    lvl_pct = round(tk.get("level_pct", 0.0), 1)
    entry = {
        "ts":     _now(),
        "evt":    event,
        "weight": net_kg,
        "level":  lvl_pct,
        **extras,
    }
    state["log"].insert(0, entry)
    state["log"] = state["log"][:200]

def _recalc_alarms():
    """Recalculate level_pct and hi/lo alarms from weight_kg."""
    tk  = state["tank"]
    net = max(0.0, tk["weight_kg"] - tk["tare_kg"])
    tk["level_pct"] = round(min(100.0, net / tk["max_kg"] * 100.0), 2) \
                      if tk["max_kg"] > 0 else 0.0
    tk["hi_alarm"]  = tk["level_pct"] >= tk["hi_threshold_pct"]
    tk["lo_alarm"]  = tk["level_pct"] <= tk["lo_threshold_pct"]

def _print_event(payload: dict):
    print(f"\n[BUTTON EVENT] {json.dumps(payload, indent=2)}")


# ══════════════════════════════════════════════════════════════════
#  INFEED HELPERS  (write directly to state — no HTTP round-trip)
# ══════════════════════════════════════════════════════════════════
def infeed_open(open_state: bool):
    """Open (True) or close (False) the infeed valve directly in state."""
    with _lock:
        state["infeed"]["valve_open"] = open_state
    
    

    print(f"[infeed] valve -> {'OPEN' if open_state else 'CLOSED'}")
    tech_log.info("Infeed valve set to %s", "OPEN" if open_state else "CLOSED")


def infeed_run_state(run_state: bool):


    """Set infeed running state directly in state."""
    with _lock:
        state["infeed"]["running"]    = run_state
        state["infeed"]["valve_open"] = run_state

    if run_state:
         gpio.output_on("out_wei_led")
    else:
         gpio.output_off("out_wei_led")

    print(f"[infeed] running -> {run_state}")
    tech_log.info("Infeed run state set to %s", run_state)





def auto_infeed_control(now_weight: float, required_weight: float,infeed_auto: bool):
    """Simple auto-control loop for AUTO mode.
    Opens the valve until the required weight is reached, then closes it.
    Does not implement any of the interrupt or safety checks of oil_add().
    """
    global weiVal
    global local_stop, infeed_remote_stop,serial_error
    infeed_open(False)
    
     
    state["ui"]["buttons"]["in-mode-btn"]["disabled"] = True
    state["ui"]["buttons"]["in-op-btn"]["disabled"] = True
    local_stop=False
    result=False
    
    gpio.output_on("ind_led_in")
    infeed_remote_stop=False
    
    while True:
        
         
        #print("wait for tank empty")
         
        if(local_stop ):
            tech_log.error("Local stop received in auto control loop.")
            print("Local stop received, exiting auto control. 1")
            state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
            state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
            local_stop=False
            break
        elif infeed_remote_stop:
            tech_log.error("Remote stop received in auto control loop.")
            print("Remote stop received, exiting auto control.")
            state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
            state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
            infeed_remote_stop=False
            break
        elif serial_error:
            tech_log.error("Serial error detected in auto control loop.")
            print("Serial error detected, exiting auto control.")
            state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
            state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
            serial_error=False
            break

        if (weiVal<state["infeed"]["auto_start_level"]) :  
                        
            result=oil_add(weiVal, required_weight,True)
            if result:
                tech_log.info("Auto fill sequence completed in auto control loop.")
                print("Auto fill done")
                state["ui"]["buttons"]["in-mode-btn"]["disabled"] = True
                state["ui"]["buttons"]["in-op-btn"]["disabled"] = True
            else:
                tech_log.warning("Auto fill sequence failed or aborted in auto control loop.")
                print("Auto fill failed or aborted.")
                state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
                state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
                break
              

        '''while(True):
            time.sleep(0.1)
            if(local_stop):
                print("Local stop received, exiting auto control.2")
                state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
                state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
                local_stop=False
                break'''
                
            


                             
                            
                            
        time.sleep(0.1)   # poll interval
    state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
    state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
    print("Exit auto control loop.")
    gpio.output_off("ind_led_in")
           


# ══════════════════════════════════════════════════════════════════
#  OIL ADDITION SEQUENCE
#  Called in a background thread when:
#    mode == MANUAL  AND  operation == LOCAL  AND  run → START
# ══════════════════════════════════════════════════════════════════
def oil_add(now_weight: float, required_weight: float,infeed_auto: bool):
    global weiVal, serial_error
    global busyFlagInfeedBusy, busyFlagOutfeedBusy
    global infeed_local_remote_change, infeed_mode_change
    global infeed_remote_stop, local_stop
    global low_level_sensor
    global hi_level_sensor
    infeed_open(False)
    gpio.output_on("ind_led_in") 
    state["ui"]["buttons"]["in-mode-btn"]["disabled"] = True
    state["ui"]["buttons"]["in-op-btn"]["disabled"] = True
    tech_log.info("oil_add requested — checking if outfeed is busy ...")

    # ── STEP 1: Wait until outfeed finishes ────────────────────────
    _waited = False
    while busyFlagOutfeedBusy:
        if not _waited:
            #gpio.output_on("in_wei_led")
            tech_log.warning("Outfeed busy — infeed waiting ...")
            print("[oil_add] Outfeed busy — waiting for outfeed to finish ...")
            _waited = True
        time.sleep(0.5)
    if _waited:
        #gpio.output_off("in_wei_led")
        tech_log.info("Outfeed cleared — proceeding with oil addition.")
        print("[oil_add] Outfeed cleared — starting.")

    # ── STEP 2: Mark infeed as busy, reset all interrupt flags ─────
    busyFlagInfeedBusy         = True
    infeed_local_remote_change = False
    local_stop                 = False
    infeed_remote_stop                = False
    infeed_mode_change         = False
    # Note: do NOT reset serial_error — it reflects live MQTT state

    intial_weight = now_weight

    tech_log.info(
        "Oil addition started. Initial: %.2f kg  Requested: %.2f kg",
        intial_weight, required_weight)
    print("Starting oil addition. Initial weight: %.2f kg, Required weight: %.2f kg"
          % (intial_weight, required_weight))

    start_time = time.time()
    
    _log("Infeed oil addition started",
         weight=round(intial_weight, 2), requested=round(required_weight, 2))

    # ── STEP 3: Weight-tracking loop ───────────────────────────────
    done = False
    result=False

    infeed_open(True)
    infeed_run_state(True)
    gpio.output_on("in_solv")

    while not done:
        elapsed = time.time() - start_time
        print(f"  Elapsed: {elapsed:.1f} s  Current weight: {weiVal:.2f} kg serial_error: {serial_error}", end="\r")
        # Timeout
        if elapsed > INFEED_TIMEOUT:
            done = True
            result=False
            tech_log.warning(
                "Oil add TIMEOUT after %ds. initial=%.2f requested=%.2f final=%.2f",
                INFEED_TIMEOUT, intial_weight, required_weight, weiVal)
            print("[oil_add] TIMEOUT after %ds — initial %.2f requested %.2f final %.2f"
                  % (INFEED_TIMEOUT, intial_weight, required_weight, weiVal))
            _log("⚠ Infeed timeout", elapsed_s=round(elapsed, 1),
                 initial=round(intial_weight, 2), requested=round(required_weight, 2),
                 final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "Oil add TIMEOUT"
            )
             
                
            if infeed_auto:
                infeed_run_state(False)
                local_stop=True
            break

        
        elif state["sensors"]["hi_level"]:
            done = True
            result=False
            tech_log.warning(
                "Oil add stopped: high level sensor triggered. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Stopped: high level sensor triggered — initial %.2f requested %.2f final %.2f"
                  % (intial_weight, required_weight, weiVal))
            _log("⚠ Infeed stopped: high level sensor",
                 initial=round(intial_weight, 2), requested=round(required_weight, 2),
                 final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "high level sensor"
            )
            break

        elif weiVal > state["tank"]["hi_level"]:
            done = True
            result=False
            tech_log.warning(
                "Oil add stopped: weight exceeded hi level. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Stopped: weight exceeded hi level — initial %.2f requested %.2f final %.2f"
                  % (intial_weight, required_weight, weiVal))
            _log("⚠ Infeed stopped: weight exceeded hi level",
                 initial=round(intial_weight, 2), requested=round(required_weight, 2),
                 final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "weight exceeded hi level"
            )
            break

        # Target reached — normal completion
        elif weiVal >= required_weight - state["tank"]["infeed_valve"] :
            done = True
            result=True
            tech_log.info(
                "Required weight reached. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Target reached — initial %.2f requested %.2f final %.2f"
                  % (intial_weight, required_weight, weiVal))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "Sucess",
            "Required weight reached"
            )

            infeed_open(False)

            if not infeed_auto:
                infeed_run_state(False)
            _log("Infeed target reached",
                 initial=round(intial_weight, 2), requested=round(required_weight, 2),
                 final=round(weiVal, 2))
            break

        # Serial / MQTT sensor error
        elif serial_error:
            done = True
            result=False
            serial_error=False
            tech_log.error("Serial error during oil addition — aborting.")
            print("[oil_add] Serial error — aborting.")
            _log("⚠ Infeed aborted: serial error", final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "serial error"
            )

            break


        if not hi_level_sensor:
            done = True
            result=False
            infeed_run_state(False)
            tech_log.warning(
                "Hi level sensor trig. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Hi level sensor trig.")
            _log("Infeed remote stop",
                 initial=round(intial_weight, 2), final=round(weiVal, 2))
            
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "Hi level sensor trig"
            )

            break


        # Remote stop signal
        elif infeed_remote_stop:
            done = True
            result=False
            infeed_run_state(False)
            tech_log.warning(
                "Remote stop. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Remote stop.")
            _log("Infeed remote stop",
                 initial=round(intial_weight, 2), final=round(weiVal, 2))
            
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "Infeed remote stop"
            )

            break

        # Local stop (operator pressed STOP on UI)
        elif local_stop:
            done = True
            result=False
            tech_log.warning(
                "Local stop. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Local stop.")
            _log("Infeed local stop",
                 initial=round(intial_weight, 2), final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "oil_add Local stop"
            )


            break

        # Mode changed mid-sequence
        elif infeed_mode_change:                
            done = True
            result=False
            tech_log.warning(
                "Mode change during oil addition. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] Mode changed — aborting.")
            _log("Infeed aborted: mode change", final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "mode change"
            )
            break

        # Operation (LOCAL/REMOTE) changed mid-sequence
        elif infeed_local_remote_change:
            done = True
            result=False
            tech_log.warning(
                "Local/Remote change during oil addition. initial=%.2f requested=%.2f final=%.2f",
                intial_weight, required_weight, weiVal)
            print("[oil_add] LOCAL/REMOTE changed — aborting.")
            _log("Infeed aborted: operation change", final=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            intial_weight,
            required_weight,
            weiVal,
            "FAIL",
            "operation change"
            )

            break

        time.sleep(0.1)   # poll interval — avoids 100 % CPU spin

    # ── STEP 4: Always clean up valve + run state ──────────────────
    infeed_open(False)
    infeed_run_state(False)
    gpio.output_off("ind_led_in") 
    gpio.output_off("in_solv")
    print("---- End filling ----")  # newline after progress line
    

    if not infeed_auto:
        infeed_run_state(False)
        state["ui"]["buttons"]["in-mode-btn"]["disabled"] = False
        state["ui"]["buttons"]["in-op-btn"]["disabled"] = False
    time.sleep(0.1)         # brief settle

    # ── STEP 5: Release busy flag ───────────────────────────────────
    busyFlagInfeedBusy = False
    tech_log.info("oil_add complete — busyFlagInfeedBusy cleared.")
    print("[oil_add] Sequence complete.")
    return result


# ══════════════════════════════════════════════════════════════════
#  OUTFEED HELPERS
# ══════════════════════════════════════════════════════════════════
def outfeed_open(open_state: bool):
    with _lock:
        state["outfeed"]["valve_open"] = open_state
    print(f"[outfeed] valve -> {'OPEN' if open_state else 'CLOSED'}")
    tech_log.info("Outfeed valve set to %s", "OPEN" if open_state else "CLOSED")


def outfeed_run_state(run_state: bool):
    with _lock:

    

        state["outfeed"]["running"]    = run_state
        state["outfeed"]["valve_open"] = run_state

    if run_state:
         gpio.output_on("in_wei_led")
    else:
         gpio.output_off("in_wei_led")

    print(f"[outfeed] running -> {run_state}")
    tech_log.info("Outfeed run state set to %s", run_state)


# ══════════════════════════════════════════════════════════════════
#  OUTFEED MANUAL SEQUENCE  (MANUAL + LOCAL + START)
#
#  Flow:
#    1. Wait until infeed finishes   (busyFlagInfeedBusy → False)
#    2. Check current oil >= requested volume (else abort with error)
#    3. Open outfeed valve and drain until weight drops by requested kg
#    4. Stop on: timeout / lo_level / lo_level_sensor / local_stop /
#               remote_stop / mode_change / operation_change
# ══════════════════════════════════════════════════════════════════
def oil_drain(requested_vol_L: float):
    global weiVal, serial_error
    global busyFlagInfeedBusy, busyFlagOutfeedBusy
    global outfeed_local_stop, outfeed_remote_stop
    global outfeed_local_remote_change, outfeed_mode_change
    global low_level_sensor,outfeed_remote_stop
    global out_feed_sucess
    tech_log.info("[outfeed] oil_drain requested — vol=%.2f L", requested_vol_L)

    # Lock buttons while sequence runs
    state["ui"]["buttons"]["out-mode-btn"]["disabled"] = True
    state["ui"]["buttons"]["out-op-btn"]["disabled"]   = True
     
    outfeed_open(False)
    outfeed_run_state(False)
    gpio.output_on("ind_led_out")
    # ── STEP 1: Wait until infeed finishes ─────────────────────────
    _waited = False
    while busyFlagInfeedBusy:
        if not _waited:
            #gpio.output_on("out_wei_led")
            tech_log.warning("[outfeed] Infeed busy — outfeed waiting ...")
            print("[oil_drain] Infeed busy — waiting for infeed to finish ...")
            _waited = True
        time.sleep(0.5)
    if _waited:
        #gpio.output_off("out_wei_led")
        tech_log.info("[outfeed] Infeed cleared — proceeding.")
        print("[oil_drain] Infeed cleared — starting drain.")

    # ── STEP 2: Mark outfeed as busy, reset flags ───────────────────
    busyFlagOutfeedBusy         = True
    outfeed_local_stop          = False
    outfeed_remote_stop         = False
    outfeed_local_remote_change = False
    outfeed_mode_change         = False

    # Convert requested volume → kg using current density
    with _lock:
        density     = state["tank"]["density_kgl"]
        current_kg  = weiVal
        lo_level    = state["tank"]["lo_level"]
        tare_kg     = state["tank"]["tare_kg"]
        max_kg      = state["tank"]["max_kg"]

    requested_kg = requested_vol_L * density

    # ── STEP 3: Pre-check — enough oil available? ───────────────────
    available_kg = max(0.0, current_kg - tare_kg)
    if requested_kg > available_kg:
        msg = (
            f"[oil_drain] ABORTED: requested {requested_kg:.2f} kg "
            f"but only {available_kg:.2f} kg available (tare={tare_kg:.2f} kg)"
        )
        tech_log.error(msg)
        print(msg)
        _log("⚠ Outfeed aborted: insufficient oil",
             requested_kg=round(requested_kg, 2),
             available_kg=round(available_kg, 2),
             current_kg=round(current_kg, 2))
        outfeed_run_state(False)
        busyFlagOutfeedBusy = False
        state["ui"]["buttons"]["out-mode-btn"]["disabled"] = False
        state["ui"]["buttons"]["out-op-btn"]["disabled"]   = False
        gpio.output_off("ind_led_out")
        return

    target_kg   = current_kg - requested_kg   # weight we expect to reach
    start_time  = time.time()

    tech_log.info(
        "[outfeed] Drain started. current=%.2f kg  requested=%.2f kg  target=%.2f kg",
        current_kg, requested_kg, target_kg)
    print("[oil_drain] Start: current=%.2f kg  drain=%.2f kg  target=%.2f kg"
          % (current_kg, requested_kg, target_kg))
    _log("Outfeed drain started",
         current_kg=round(current_kg, 2),
         requested_kg=round(requested_kg, 2),
         target_kg=round(target_kg, 2))

    outfeed_open(True)
    outfeed_run_state(True)
    gpio.output_on("out_solv")
    # ── STEP 4: Drain loop ──────────────────────────────────────────
    done = False
    while not done:
        elapsed = time.time() - start_time

        if elapsed > OUTFEED_TIMEOUT:
            done = True
            tech_log.warning(
                "[outfeed] TIMEOUT after %ds. target=%.2f final=%.2f",
                OUTFEED_TIMEOUT, target_kg, weiVal)
            print("[oil_drain] TIMEOUT after %ds" % OUTFEED_TIMEOUT)
            _log("⚠ Outfeed timeout",
                 elapsed_s=round(elapsed, 1),
                 target_kg=round(target_kg, 2),
                 final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "FAIL",
            "[oil_drain] TIMEOUT"
            )

            break

 
        elif out_feed_sucess:
            out_feed_sucess=False
            done = True
            tech_log.info(
                "[outfeed] Oven request to stop. requested=%.2f kg  final=%.2f kg",
                requested_kg, weiVal)
            print("[oil_drain] Oven request to stop — drained %.2f kg" % (current_kg - weiVal))
            outfeed_open(False)
            outfeed_run_state(False)
            _log("Outfeed Oven request to stop",
                 requested_kg=round(requested_kg, 2),
                 drained_kg=round(current_kg - weiVal, 2),
                 final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Sucess",
            "Outfeed Oven request to stop"
            )
            break
        # Tank too low — stop draining
        elif weiVal<= lo_level or low_level_sensor:
            done = True
            reason = "low level sensor" if low_level_sensor else "lo_level threshold"
            tech_log.warning("[outfeed] Stopped: %s. final=%.2f kg", reason, weiVal)
            print("[oil_drain] Stopped: %s" % reason)
            _log(f"⚠ Outfeed stopped: {reason}", final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "FAIL",
            reason
            )
            break

        elif outfeed_remote_stop:
            done = True
            outfeed_remote_stop=False
            tech_log.warning("[outfeed] Remote stop.")
            print("[oil_drain] Remote stop.")
            _log("Outfeed remote stop", final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "FAIL",
            "[outfeed] Remote stop"
            )
            break

        # Target reached —external sig
        

        # Target reached — normal completion
        elif weiVal <= target_kg:
            done = True
            tech_log.info(
                "[outfeed] Target reached. requested=%.2f kg  final=%.2f kg",
                requested_kg, weiVal)
            print("[oil_drain] Target reached — drained %.2f kg" % (current_kg - weiVal))
            outfeed_open(False)
            outfeed_run_state(False)
            _log("Outfeed target reached",
                 requested_kg=round(requested_kg, 2),
                 drained_kg=round(current_kg - weiVal, 2),
                 final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Sucess",
            "Outfeed target reached"
            )
            break

        elif serial_error:
            serial_error=False
            done = True
            tech_log.error("[outfeed] Serial error — aborting.")
            print("[oil_drain] Serial error — aborting.")
            _log("⚠ Outfeed aborted: serial error", final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Fail",
            "[oil_drain] Serial error"
            )
            break

        elif outfeed_local_stop:
            done = True
            tech_log.info("[outfeed] Local stop.")
            print("[oil_drain] Local stop.")
            _log("Outfeed local stop",
                 drained_kg=round(current_kg - weiVal, 2),
                 final_kg=round(weiVal, 2))
            
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Fail",
            "[oil_drain] Local stop"
            )
            break

         
        elif outfeed_mode_change:
            done = True
            tech_log.warning("[outfeed] Mode changed mid-sequence — aborting.")
            _log("Outfeed aborted: mode change", final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Fail",
            "Outfeed aborted: mode change"
            )
            break

        elif outfeed_local_remote_change:
            done = True
            tech_log.warning("[outfeed] Operation changed mid-sequence — aborting.")
            _log("Outfeed aborted: operation change", final_kg=round(weiVal, 2))
            prod_logger.log(
            state["product"],
            current_kg,
            requested_kg,
            weiVal,
            "Fail",
            "Outfeed aborted: operation change"
            )
            break

        time.sleep(0.1)

    # ── STEP 5: Always clean up ─────────────────────────────────────
    outfeed_open(False)
    outfeed_run_state(False)
    gpio.output_off("out_solv")
    gpio.output_off("ind_led_out")
    time.sleep(0.1)

    busyFlagOutfeedBusy = False
    state["ui"]["buttons"]["out-mode-btn"]["disabled"] = False
    state["ui"]["buttons"]["out-op-btn"]["disabled"]   = False
    tech_log.info("[outfeed] oil_drain complete — busyFlagOutfeedBusy cleared.")
    print("[oil_drain] Sequence complete.")


# ══════════════════════════════════════════════════════════════════
#  OUTFEED AUTO SEQUENCE  (AUTO + LOCAL + START)
#
#  Same safety guards as MANUAL (wait for infeed, timeout,
#  lo_level, lo_level_sensor, stop signals).
#  The actual drain logic is intentionally left empty — add your
#  AUTO outfeed business logic here when ready.
# ══════════════════════════════════════════════════════════════════
def auto_outfeed_control():
    global weiVal, serial_error
    global busyFlagInfeedBusy, busyFlagOutfeedBusy
    global outfeed_local_stop, outfeed_remote_stop
    global outfeed_local_remote_change, outfeed_mode_change
    global low_level_sensor

    tech_log.info("[outfeed AUTO] auto_outfeed_control started.")
    print("[auto_outfeed] Started.")

    state["ui"]["buttons"]["out-mode-btn"]["disabled"] = True
    state["ui"]["buttons"]["out-op-btn"]["disabled"]   = True

    # ── Wait until infeed finishes ──────────────────────────────────
    _waited = False
    while busyFlagInfeedBusy:
        if not _waited:
            #gpio.output_on("out_wei_led")
            tech_log.warning("[outfeed AUTO] Infeed busy — waiting ...")
            print("[auto_outfeed] Infeed busy — waiting ...")
            _waited = True
        # Check for stop while waiting
        if outfeed_local_stop or outfeed_remote_stop:
            tech_log.info("[outfeed AUTO] Stop requested while waiting for infeed.")
            outfeed_run_state(False)
            busyFlagOutfeedBusy = False
            state["ui"]["buttons"]["out-mode-btn"]["disabled"] = False
            state["ui"]["buttons"]["out-op-btn"]["disabled"]   = False
            return
        time.sleep(0.5)
    if _waited:
        #gpio.output_off("out_wei_led")
        tech_log.info("[outfeed AUTO] Infeed cleared — proceeding.")

    busyFlagOutfeedBusy         = True
    outfeed_local_stop          = False
    outfeed_remote_stop         = False
    outfeed_local_remote_change = False
    outfeed_mode_change         = False

    with _lock:
        lo_level   = state["tank"]["lo_level"]
        start_kg   = weiVal

    tech_log.info("[outfeed AUTO] Running. current=%.2f kg", start_kg)
    _log("Outfeed AUTO sequence started", current_kg=round(start_kg, 2))

    start_time = time.time()
    
    # ── AUTO drain loop — add your logic inside here ────────────────
    gpio.output_on("out_solv")

    done = False
    while not done:
        elapsed = time.time() - start_time

        if elapsed > OUTFEED_TIMEOUT:
            done = True
            tech_log.warning("[outfeed AUTO] TIMEOUT after %ds.", OUTFEED_TIMEOUT)
            print("[auto_outfeed] TIMEOUT after %ds" % OUTFEED_TIMEOUT)
            _log("⚠ Outfeed AUTO timeout", elapsed_s=round(elapsed, 1))
            prod_logger.log(
            state["product"],
            start_kg,
            weiVal,
            weiVal,
            "Fail",
            "this cannot happen"
            )
            break

        elif weiVal<= lo_level or low_level_sensor:
            done = True
            reason = "low level sensor" if low_level_sensor else "lo_level threshold"
            tech_log.warning("[outfeed AUTO] Stopped: %s", reason)
            print("[auto_outfeed] Stopped: %s" % reason)
            _log(f"⚠ Outfeed AUTO stopped: {reason}", final_kg=round(weiVal, 2))
            break

        elif serial_error:
            done = True
            tech_log.error("[outfeed AUTO] Serial error — aborting.")
            _log("⚠ Outfeed AUTO aborted: serial error")
            break

        elif outfeed_local_stop:
            done = True
            tech_log.info("[outfeed AUTO] Local stop.")
            _log("Outfeed AUTO local stop", final_kg=round(weiVal, 2))
            break

        elif outfeed_remote_stop:
            done = True
            tech_log.info("[outfeed AUTO] Remote stop.")
            _log("Outfeed AUTO remote stop", final_kg=round(weiVal, 2))
            break

        elif outfeed_mode_change:
            done = True
            tech_log.warning("[outfeed AUTO] Mode changed — aborting.")
            _log("Outfeed AUTO aborted: mode change")
            break

        elif outfeed_local_remote_change:
            done = True
            tech_log.warning("[outfeed AUTO] Operation changed — aborting.")
            _log("Outfeed AUTO aborted: operation change")
            break

        # ── YOUR AUTO OUTFEED LOGIC GOES HERE ──────────────────────

        time.sleep(0.1)

    # ── Cleanup ─────────────────────────────────────────────────────
    outfeed_open(False)
    outfeed_run_state(False)
    gpio.output_off("out_solv")
    time.sleep(0.1)

    busyFlagOutfeedBusy = False
    state["ui"]["buttons"]["out-mode-btn"]["disabled"] = False
    state["ui"]["buttons"]["out-op-btn"]["disabled"]   = False
    tech_log.info("[outfeed AUTO] Complete — busyFlagOutfeedBusy cleared.")
    print("[auto_outfeed] Sequence complete.")

# ══════════════════════════════════════════════════════════════════
#  MQTT CALLBACKS  (run inside paho's network thread)
# ══════════════════════════════════════════════════════════════════
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        with _lock:
            state["mqtt"]["connected"] = True
        print(f"\n[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}  topic={MQTT_TOPIC}")
        tech_log.info("MQTT connected. Subscribed to %s", MQTT_TOPIC)
    else:
        print(f"\n[MQTT] Connection failed  rc={rc}")
        tech_log.error("MQTT connection failed rc=%s", rc)


def on_disconnect(client, userdata, rc):
    with _lock:
        state["mqtt"]["connected"] = False
    tech_log.warning("MQTT disconnected rc=%s", rc)
    print(f"\n[MQTT] Disconnected (rc={rc}) — paho will auto-reconnect")


def on_message_weight(client, userdata, msg):
    """
    Your original callback — unchanged logic.
    Parses weiVal, sets serial_error, and syncs into shared state.
    """
    global weiVal, serial_error

    payload_str = msg.payload.decode()

    try:
        if payload_str.startswith("#"):
            # ── Error frame from sensor ─────────────────────────
            print(f"\n[MQTT] Error frame: {payload_str}")
            tech_log.error("Error message received from MQTT: %s", payload_str)
            serial_error = True
            with _lock:
                state["mqtt"]["serial_error"] = True
                state["mqtt"]["last_value"]   = payload_str
            _log(f"⚠ MQTT sensor error: {payload_str}")
            time.sleep(10)     # same delay as your original code

        else:
            # ── Good numeric reading ─────────────────────────────
            weiVal       = float(payload_str)
            #serial_error = False

            with _lock:
                # Push weight into tank state
                state["tank"]["weight_kg"]    = weiVal
                state["mqtt"]["serial_error"] = False
                state["mqtt"]["last_value"]   = weiVal
                state["mqtt"]["last_ts"]      = _now()
                # Recalculate level % and alarms from new weight
                _recalc_alarms()

            '''print(
                f"[MQTT] weight = {weiVal:.2f} kg"
                f"  level = {state['tank']['level_pct']:.2f}%"
            )
            tech_log.info(
                "weight=%.2f kg  level=%.2f%%",
                weiVal, state["tank"]["level_pct"]
            )'''

    except ValueError:
        print(f"\n[MQTT] Non-numeric payload: {payload_str!r}")
        tech_log.error("Received non-numeric weight value: %s", payload_str)
        weiVal       = 0.0
        serial_error = True
        with _lock:
            state["mqtt"]["serial_error"] = True
            state["mqtt"]["last_value"]   = payload_str
        _log(f"⚠ MQTT parse error: {payload_str}")


# ══════════════════════════════════════════════════════════════════
#  MQTT THREAD  (started as daemon before Flask)
# ══════════════════════════════════════════════════════════════════
def _mqtt_thread():
    """
    Separate daemon thread.
    Uses paho loop_forever() with built-in auto-reconnect.
    """
    if not MQTT_AVAILABLE:
        print("[MQTT] Thread not started — paho-mqtt not installed.")
        return

    client = mqtt_client.Client(client_id="ols-monitor", clean_session=True)

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message_weight

    # Exponential back-off: 1 s min, 30 s max between reconnect attempts
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    while True:
        try:
            print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()          # blocks; reconnects automatically
        except Exception as exc:
            tech_log.error("MQTT fatal error: %s — retry in 5 s", exc)
            print(f"[MQTT] Error: {exc} — retrying in 5 s")
            with _lock:
                state["mqtt"]["connected"] = False
            time.sleep(5)


# ══════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/data")
def api_data():
    with _lock:
        state["timestamp"] = _now()
        
        return jsonify(state)


# ─────────────────────────────────────────────────────────────────
# POST /api/control  — all button clicks arrive here
# ─────────────────────────────────────────────────────────────────
@app.route("/api/control", methods=["POST"])
def api_control():
    body   = request.get_json(force=True)
    side   = body.get("side")
    action = body.get("action")
    global local_stop, infeed_remote_stop, infeed_mode_change, infeed_local_remote_change
    global outfeed_local_stop, outfeed_remote_stop, outfeed_mode_change, outfeed_local_remote_change

    with _lock:

        # ── Settings save ──────────────────────────────────────────
        if side == "_settings" and action == "save_settings":
            data = body.get("data", {})
            state.update({
                "product":      data.get("product",      state["product"]),
                "product_code": data.get("product_code", state["product_code"]),
            })
            for k in ("max_kg", "density_kgl", "tare_kg",
                      "hi_threshold_pct", "lo_threshold_pct"):
                if k in data.get("tank", {}):
                    state["tank"][k] = data["tank"][k]
            if "manual_vol_L" in data.get("infeed", {}):
                state["infeed"]["manual_vol_L"] = data["infeed"]["manual_vol_L"]
            _recalc_alarms()
            _print_event({"action": "save_settings", "status": "ok"})
            _log("Settings saved")
             
            return jsonify({"ok": True})

        if side not in ("infeed", "outfeed"):
            return jsonify({"error": "unknown side"}), 400

        s = state[side]

        if action == "mode":
            s["mode"] = "MANUAL" if s["mode"] == "AUTO" else "AUTO"
            _print_event({"side": side, "button": "mode", "value": s["mode"]})
            _log(f"{side.capitalize()} mode -> {s['mode']}")
            # Signal oil_add loop if infeed sequence is running
            if side == "infeed" and busyFlagInfeedBusy:
                infeed_mode_change = True
            if side == "outfeed" and busyFlagOutfeedBusy:
                outfeed_mode_change = True

        elif action == "operation":
            s["operation"] = "REMOTE" if s["operation"] == "LOCAL" else "LOCAL"
            if side =="outfeed" and s["operation"] == "REMOTE":
                

                s["mode"]="AUTO"
            elif side =="outfeed" and s["operation"] == "LOCAL":
            
                s["mode"]="MANUAL"

            _print_event({"side": side, "button": "operation", "value": s["operation"]})
            _log(f"{side.capitalize()} operation -> {s['operation']}")
            # Signal oil_add loop if infeed sequence is running
            if side == "infeed" and busyFlagInfeedBusy:
                infeed_local_remote_change = True
            if side == "outfeed" and busyFlagOutfeedBusy:
                outfeed_local_remote_change = True

        elif action == "run":
            s["running"]    = not s["running"]
            s["valve_open"] = s["running"]
            '''_print_event({
                "side":   side,
                "button": "run",
                "value":  "START" if s["running"] else "STOP",
                "state":  s["running"],
            })'''
            _log(f"{side.capitalize()} -> {'START' if s['running'] else 'STOP'}")

            # ── Infeed MANUAL + LOCAL: launch / abort oil_add sequence ──
            if side == "infeed":

                if   s["operation"] == "REMOTE":
                    if gpio.state("intake_mode"):
                        s["mode"] == "MANUAL"
                    else:
                        s["mode"] == "AUTO"



                
                if s["running"] and s["mode"] == "MANUAL" and s["operation"] == "LOCAL":
                    # START → spawn oil_add in background thread
                    # Snapshot the weight and requested volume BEFORE releasing lock
                    _now_w = weiVal
                    _req_w = state["infeed"]["manual_vol_L"]
                    t = threading.Thread(
                        target=oil_add,
                        args=(_now_w, _req_w,False),
                        daemon=True,
                        name="infeed_manual_local_thread",
                    )
                    t.start()
                    tech_log.info(
                        "oil_add thread started local manual — now=%.2f kg  requested=%.2f kg",
                        _now_w, _req_w)
                    print(f"[infeed local manual ] oil_add thread started  now={_now_w:.2f} kg  req={_req_w:.2f} kg")

                elif s["running"] and s["mode"] == "AUTO" and s["operation"] == "LOCAL":
                    _now_w = weiVal
                    _req_w = state["infeed"]["manual_vol_L"]
                    # START in AUTO mode → just open the valve, no thread
                    tech_log.info(
                        "oil_add thread started local auto — now=%.2f kg  requested=%.2f kg",
                        _now_w, _req_w)
                    print(f"[infeed local auto ] oil_add thread started  now={_now_w:.2f} kg  req={_req_w:.2f} kg")
                    t = threading.Thread(
                        target=auto_infeed_control,
                        args=(_now_w, _req_w,True),
                        daemon=True,
                        name="infeed_auto_local_thread",
                    )
                    t.start()

                elif s["operation"] == "REMOTE":
                    state["infeed"]["running"] = False


                elif not s["running"]:
                    # STOP pressed → signal the running oil_add loop to exit
                    local_stop = True
                    tech_log.info("Local stop signalled to oil_add.")

            # ── Outfeed run handling ────────────────────────────────
            if side == "outfeed":
                
                
                
                if s["running"] and s["mode"] == "MANUAL" and s["operation"] == "LOCAL":
                    _req_vol = state["outfeed"]["manual_vol_L"]
                    t = threading.Thread(
                        target=oil_drain,
                        args=(_req_vol,),
                        daemon=True,
                        name="outfeed_manual",
                    )
                    t.start()
                    tech_log.info("[outfeed] oil_drain thread local started — vol=%.2f L", _req_vol)
                    print(f"[outfeed] oil_drain local thread started  vol={_req_vol:.2f} L")

                elif s["running"] and s["mode"] == "AUTO" and s["operation"] == "LOCAL":
                    t = threading.Thread(
                        target=auto_outfeed_control,
                        daemon=True,
                        name="outfeed_auto",
                    )
                    t.start()
                    tech_log.info("[outfeed] auto_outfeed_control thread started.")
                    print("[outfeed] AUTO sequence thread started.")

                elif not s["running"]:
                    outfeed_local_stop = True
                    tech_log.info("[outfeed] Local stop signalled.")
                 


        elif action == "valve":
            s["valve_open"] = bool(body.get("state", False))
            _print_event({
                "side":   side,
                "button": "valve",
                "value":  "OPEN" if s["valve_open"] else "CLOSED",
                "state":  s["valve_open"],
            })
            _log(f"{side.capitalize()} valve -> {'OPEN' if s['valve_open'] else 'CLOSED'}")

        elif action == "apply":
            vol = float(body.get("vol", 0))
            if vol <= 0:
                return jsonify({"error": "volume must be > 0"}), 400

            # Save to state
            state[side]["manual_vol_L"] = vol

            # Save to config.yml
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")
                with open(cfg_path) as f:
                    cfg = yaml.safe_load(f) or {}
                cfg.setdefault(side, {})["manual_vol_L"] = vol
                with open(cfg_path, "w") as f:
                    yaml.safe_dump(cfg, f)
                tech_log.info("manual_vol_L %.2f L saved to config.yml [%s]", vol, side)
            except Exception as e:
                tech_log.error("Failed to save manual_vol_L: %s", e)

            _print_event({"side": side, "button": "apply_volume", "vol_L": vol})
            _log(f"{side.capitalize()} volume set to {vol} L")


        else:
            return jsonify({"error": f"unknown action: {action}"}), 400

    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────
# POST /api/update  — push any value from external Python script
#   {"path": "tank.weight_kg", "value": 520.5}
# ─────────────────────────────────────────────────────────────────
@app.route("/api/update", methods=["POST"])
def api_update():
    body  = request.get_json(force=True)
    path  = body.get("path", "")
    value = body.get("value")
    parts = path.split(".")

    with _lock:
        if len(parts) == 1:
            if parts[0] in state:
                state[parts[0]] = value
                print(f"\n[API UPDATE] {path} = {json.dumps(value)}")
            else:
                return jsonify({"error": f"unknown key: {path}"}), 400
        elif len(parts) == 2:
            section, key = parts
            if section in state and isinstance(state[section], dict):
                state[section][key] = value
                print(f"\n[API UPDATE] {path} = {json.dumps(value)}")
                if section == "tank":
                    _recalc_alarms()
            else:
                return jsonify({"error": f"unknown path: {path}"}), 400
        else:
            return jsonify({"error": "path depth > 2 not supported"}), 400

    return jsonify({"ok": True, "path": path, "value": value})


# ─────────────────────────────────────────────────────────────────
# POST /api/buttons — enable / disable any button
#   {"button": "in-run-btn", "disabled": true}
# ─────────────────────────────────────────────────────────────────
@app.route("/api/buttons", methods=["POST"])
def api_buttons():
    body     = request.get_json(force=True)
    btn_id   = body.get("button")
    disabled = bool(body.get("disabled", False))

    with _lock:
        btns = state["ui"]["buttons"]
        if btn_id not in btns:
            return jsonify({"error": f"unknown button: {btn_id}"}), 400
        btns[btn_id]["disabled"] = disabled

    print(f"\n[API BUTTONS] {btn_id} -> {'DISABLED' if disabled else 'ENABLED'}")
    return jsonify({"ok": True, "button": btn_id, "disabled": disabled})


# ─────────────────────────────────────────────────────────────────
# DELETE /api/log
# ─────────────────────────────────────────────────────────────────
@app.route("/api/log", methods=["DELETE"])
def api_log_clear():
    with _lock:
        state["log"].clear()
    print("\n[LOG] Cleared")
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────
# GET /api/log/csv  — last 20 rows from the latest production CSV
# ─────────────────────────────────────────────────────────────────
@app.route("/api/log/csv", methods=["GET"])
def api_log_csv():
    import csv, glob
    # Find all CSV files in LOG_DIR, pick the newest by filename (date-sorted)
    pattern = os.path.join(LOG_DIR, "*.csv")
    files   = sorted(glob.glob(pattern))
    if not files:
        return jsonify([])
    latest = files[-1]   # alphabetical sort works for YYYY-MM-DD filenames
    rows = []
    try:
        with open(latest, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        tech_log.error("Failed to read CSV log %s: %s", latest, e)
        return jsonify([])
    # Return last 20 rows, newest first
    return jsonify(list(reversed(rows[-20:])))


# ─────────────────────────────────────────────────────────────────
# GET /api/products  — read products.csv beside config.yml
#   Returns: [{"code": "OIL-001", "name": "Crude Oil"}, ...]
# ─────────────────────────────────────────────────────────────────
@app.route("/api/products", methods=["GET"])
def api_products():
    import csv
    cfg_dir      = os.path.dirname(os.path.abspath(__file__))
    products_csv = os.path.join(cfg_dir, "products.csv")
    products     = []
    try:
        with open(products_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("code") or "").strip()
                name = (row.get("name") or "").strip()
                if code and name:
                    products.append({"code": code, "name": name})
    except FileNotFoundError:
        tech_log.warning("products.csv not found at %s", products_csv)
    return jsonify(products)


# ─────────────────────────────────────────────────────────────────
# POST /api/settings  — save all settings to config.yml + update state
# ─────────────────────────────────────────────────────────────────
@app.route("/api/settings", methods=["POST"])
def api_settings():
    body = request.get_json(force=True)

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")
    try:
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}

    if "product_code" in body:
        cfg["product_code"] = body["product_code"]
        state["product_code"] = body["product_code"]
    if "product" in body:
        cfg["product"] = body["product"]
        state["product"] = body["product"]

    if "serial" in body:
        cfg.setdefault("serial", {})
        cfg["serial"]["port"]     = body["serial"].get("port", cfg["serial"].get("port", "/dev/ttyUSB0"))
        cfg["serial"]["baudrate"] = int(body["serial"].get("baudrate", cfg["serial"].get("baudrate", 9600)))
        state.setdefault("serial", {})
        state["serial"]["port"]     = cfg["serial"]["port"]
        state["serial"]["baudrate"] = cfg["serial"]["baudrate"]

    if "tank" in body:
        t  = body["tank"]
        cfg.setdefault("tank", {})
        tk = state["tank"]
        for key in ("max_kg", "density_kgl", "tare_kg", "infeed_valve",
                    "hi_level_kg", "hi_threshold_pct", "lo_level_kg", "lo_threshold_pct"):
            if key in t:
                val = float(t[key])
                cfg["tank"][key] = val
                if key in tk:
                    tk[key] = val
        _recalc_alarms()

    if "infeed" in body:
        i = body["infeed"]
        cfg.setdefault("infeed", {})
        if "filling_time" in i: cfg["infeed"]["filling_time"] = int(i["filling_time"])
        if "manual_vol_L" in i:
            cfg["infeed"]["manual_vol_L"] = float(i["manual_vol_L"])
            state["infeed"]["manual_vol_L"] = float(i["manual_vol_L"])

    if "outfeed" in body:
        o = body["outfeed"]
        cfg.setdefault("outfeed", {})
        if "draining_time" in o: cfg["outfeed"]["draining_time"] = int(o["draining_time"])
        if "manual_vol_L"  in o:
            cfg["outfeed"]["manual_vol_L"] = float(o["manual_vol_L"])
            state["outfeed"]["manual_vol_L"] = float(o["manual_vol_L"])

    try:
        with open(cfg_path, "w") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=True)
        tech_log.info("[SETTINGS] saved to config.yml")
        print("[SETTINGS] config.yml updated")
    except Exception as e:
        tech_log.error("[SETTINGS] Failed to write config.yml: %s", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})

# ── DAILY 6 AM SCHEDULER THREAD ────────────────────────────────────
def daily_6am_scheduler():
    """Polls time. Runs job once at/after 6 AM (flag=0), resets flag at 7 AM."""
    while True:
        now = datetime.now()
        hour = now.hour

        # Read current flag from config
        try:
            with open("config.yml") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            tech_log.error("[SCHEDULER] Failed to read config.yml: %s", e)
            time.sleep(60)
            continue

        job_done = cfg.get("daily_job_done", 0)

        # 6 AM or later AND job not done yet → run it
        if hour == 6 and job_done == 0:
            import  emailsend  as em

            latest_file = em.get_latest_csv("/home/palmoil/stuff/logs")
            print("Latest file:", latest_file)
            tech_log.info("[SCHEDULER] Running daily 6 AM job...{latest_file}")
            print("[SCHEDULER] Running daily 6 AM job —", now.strftime("%Y-%m-%d %H:%M:%S"))
            
            em.send_email(
            "Production Report",
            "Daily production report attached.",
            "amalanjula@gmail.com",
            latest_file
            )


            # ── YOUR JOB CODE HERE ──────────────────────
            
            # ───────────────────────────────────────────

            # Write flag = 1 to config
            cfg["daily_job_done"] = 1
            with open("config.yml", "w") as f:
                yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=True)
            tech_log.info("[SCHEDULER] Job done. Flag set to 1.")

        # 7 AM or later AND flag is 1 → reset it
        elif hour >= 7 and job_done == 1:
            cfg["daily_job_done"] = 0
            with open("config.yml", "w") as f:
                yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=True)
            tech_log.info("[SCHEDULER] Flag reset to 0.")

        time.sleep(5)  # check every minute


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  OLS Monitor Server")
    print(f"  UI     ->  http://localhost:5000")
    print(f"  Broker ->  {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Topic  ->  {MQTT_TOPIC}")
    print("=" * 60)
    
    t = threading.Thread(target=daily_6am_scheduler, name="daily-scheduler", daemon=True)
    t.start()

    # Start MQTT in its own daemon thread BEFORE Flask
    t = threading.Thread(target=_mqtt_thread, name="mqtt-weight", daemon=True)
    t.start()
    print(f"[MQTT] Thread started (id={t.ident})\n")

    t = threading.Thread(target=gpio_handler, name="gpio-handler", daemon=True)
    t.start()

    # Start Flask (use_reloader=False required when using threads)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)