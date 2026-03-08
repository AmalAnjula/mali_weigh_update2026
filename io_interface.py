#!/usr/bin/env python3
"""
io_interface.py  —  Physical I/O ↔ MQTT Bridge
================================================
Reads 32-bit digital inputs, writes 32-bit digital outputs.
Communicates with app.py exclusively via MQTT.

──────────────────────────────────────────────────────────────────
  MQTT TOPICS
──────────────────────────────────────────────────────────────────
  Published (inputs → broker):
    ols/io/input/{name}      value: "1" or "0"   on every change
    ols/io/inputs            JSON snapshot of all inputs          1 Hz

  Subscribed (broker → outputs):
    ols/io/output/{name}     value: "1" or "0"   set physical pin

  Status:
    ols/io/status            JSON heartbeat                       1 Hz

──────────────────────────────────────────────────────────────────
  HARDWARE ABSTRACTION
──────────────────────────────────────────────────────────────────
  Swap in your real hardware by editing the two functions at the
  bottom of the HAL section:
    _hal_read_all_inputs()   → returns dict {name: 0|1}
    _hal_write_output(name, value)  → sets physical pin/register

  Default HAL is a SOFTWARE SIMULATOR so the script runs without
  any hardware attached (useful for testing).
──────────────────────────────────────────────────────────────────
"""

import os, json, time, logging, logging.handlers, threading, yaml
import paho.mqtt.client as mqtt

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════
CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

with open(CFG_PATH) as f:
    CONFIG = yaml.safe_load(f)

MQTT_BROKER = CONFIG.get("mqtt", {}).get("broker",  "localhost")
MQTT_PORT   = CONFIG.get("mqtt", {}).get("port",    1883)
MQTT_USER   = CONFIG.get("mqtt", {}).get("user",    "")
MQTT_PASS   = CONFIG.get("mqtt", {}).get("password","")

POLL_HZ     = CONFIG.get("io", {}).get("poll_hz",  20)   # input scan rate
POLL_SLEEP  = 1.0 / POLL_HZ

# MQTT topic roots
T_INPUT     = "ols/io/input"      # ols/io/input/{name}
T_INPUTS    = "ols/io/inputs"     # full JSON snapshot
T_OUTPUT    = "ols/io/output"     # ols/io/output/{name}
T_STATUS    = "ols/io/status"

# ══════════════════════════════════════════════════════════════════
#  PIN MAP  — edit to match your 32-bit I/O module addresses
#  Each entry:  name → pin/register index (0-based)
# ══════════════════════════════════════════════════════════════════
INPUT_PINS: dict[str, int] = {
    # ── Infeed controls ────────────────────────────────
    "infeed_auto":          0,
    "infeed_start":         1,
    "infeed_stop":          2,
    # ── Outfeed controls ───────────────────────────────
    "outfeed_auto":         3,
    "outfeed_start":        4,
    "outfeed_stop":         5,
    # ── Level sensors ──────────────────────────────────
    "low_level_sensor":     6,
    "hi_level_sensor":      7,
    # ── Valve feedback / position ──────────────────────
    "invalve_open":         8,
    "invalve_close":        9,
    "outvalve_open":        10,
    "outvalve_close":       11,
    # ── Panel ──────────────────────────────────────────
    "lock_button":          12,
    "power_pin":            13,
}

OUTPUT_PINS: dict[str, int] = {
    # ── Status LEDs ────────────────────────────────────
    "in_waiting_led":       0,
    "out_waiting_led":      1,
    "alarm_led":            2,
    "power_led":            3,
    "indicator_led_in":     4,
    "indicator_led_out":    5,
    # ── Relay / solenoids ──────────────────────────────
    "relay":                6,
    "input_solenoid":       7,
    "output_solenoid":      8,
}

# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")

def _fh(name):
    h = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, name), when="midnight", backupCount=30, encoding="utf-8")
    h.setFormatter(_fmt)
    return h

logging.basicConfig(level=logging.DEBUG, handlers=[])
log = logging.getLogger("ols.io")
log.addHandler(logging.StreamHandler())
log.addHandler(_fh("ols_io.log"))
log.handlers[0].setFormatter(_fmt)
log.setLevel(logging.DEBUG)

# ══════════════════════════════════════════════════════════════════
#  SHARED STATE
# ══════════════════════════════════════════════════════════════════
_lock = threading.Lock()

# Last known state of every input (used to detect edges)
_input_state:  dict[str, int] = {k: 0 for k in INPUT_PINS}
# Desired state of every output  (written to hardware by output thread)
_output_state: dict[str, int] = {k: 0 for k in OUTPUT_PINS}
# Track MQTT connected status
_mqtt_connected = False

# ══════════════════════════════════════════════════════════════════
#  HARDWARE ABSTRACTION LAYER  (HAL)
#  ─────────────────────────────────────────────────────────────────
#  Replace these two functions with your real hardware driver.
#  Examples at the bottom of this section for RPi GPIO / Modbus.
# ══════════════════════════════════════════════════════════════════
try:
    # ── Option A: Raspberry Pi GPIO ────────────────────────────────
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    for _pin in INPUT_PINS.values():
        GPIO.setup(_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    for _pin in OUTPUT_PINS.values():
        GPIO.setup(_pin, GPIO.OUT, initial=GPIO.LOW)
    _HW = "rpi"
    log.info("HAL: Raspberry Pi GPIO initialised.")

except ImportError:
    try:
        # ── Option B: Modbus TCP (pymodbus) ────────────────────────
        from pymodbus.client import ModbusTcpClient as _ModbusClient
        _modbus = _ModbusClient(
            host=CONFIG.get("io", {}).get("modbus_host", "192.168.1.100"),
            port=CONFIG.get("io", {}).get("modbus_port", 502),
        )
        _modbus.connect()
        _HW = "modbus"
        log.info("HAL: Modbus TCP client connected.")

    except ImportError:
        # ── Option C: Software simulator (no hardware needed) ──────
        import random as _rnd
        _sim_inputs: dict[str, int] = {k: 0 for k in INPUT_PINS}
        _HW = "sim"
        log.warning("HAL: No hardware library found — running in SIMULATOR mode.")


def _hal_read_all_inputs() -> dict[str, int]:
    """Return {name: 0|1} for all defined inputs."""
    result: dict[str, int] = {}

    if _HW == "rpi":
        for name, pin in INPUT_PINS.items():
            result[name] = 0 if GPIO.input(pin) else 1   # active-low: adjust if needed

    elif _HW == "modbus":
        try:
            rr = _modbus.read_discrete_inputs(address=0, count=32)
            bits = rr.bits if not rr.isError() else [0] * 32
            for name, idx in INPUT_PINS.items():
                result[name] = int(bits[idx]) if idx < len(bits) else 0
        except Exception as exc:
            log.error("Modbus read error: %s", exc)
            result = {k: 0 for k in INPUT_PINS}

    else:  # simulator
        for name in INPUT_PINS:
            result[name] = _sim_inputs.get(name, 0)

    return result


def _hal_write_output(name: str, value: int):
    """Set one physical output to 0 or 1."""
    if name not in OUTPUT_PINS:
        return

    if _HW == "rpi":
        GPIO.output(OUTPUT_PINS[name], GPIO.HIGH if value else GPIO.LOW)

    elif _HW == "modbus":
        try:
            _modbus.write_coil(OUTPUT_PINS[name], bool(value))
        except Exception as exc:
            log.error("Modbus write error [%s=%d]: %s", name, value, exc)

    else:  # simulator — just log
        log.debug("[SIM] output %s -> %d", name, value)


# ── Simulator helper: set a simulated input from MQTT or test code ─
def _sim_set_input(name: str, value: int):
    if _HW == "sim" and name in _sim_inputs:
        _sim_inputs[name] = value


# ══════════════════════════════════════════════════════════════════
#  EDGE DETECTION  (rising / falling)
# ══════════════════════════════════════════════════════════════════
def _detect_edges(new_states: dict[str, int]) -> list[tuple[str, int, int]]:
    """
    Compare new_states with _input_state.
    Returns list of (name, old_val, new_val) for changed pins.
    """
    edges = []
    for name, new_val in new_states.items():
        old_val = _input_state.get(name, 0)
        if new_val != old_val:
            edges.append((name, old_val, new_val))
    return edges


# ══════════════════════════════════════════════════════════════════
#  MQTT CALLBACKS
# ══════════════════════════════════════════════════════════════════
_mqtt_client: mqtt.Client = None   # set in main

def on_connect(client, userdata, flags, rc):
    global _mqtt_connected
    if rc == 0:
        _mqtt_connected = True
        client.subscribe(f"{T_OUTPUT}/#")
        # Also subscribe to sim input injection for testing
        client.subscribe("ols/io/sim/input/#")
        log.info("MQTT connected. Subscribed to %s/#", T_OUTPUT)
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    else:
        _mqtt_connected = False
        log.error("MQTT connection failed rc=%s", rc)


def on_disconnect(client, userdata, rc):
    global _mqtt_connected
    _mqtt_connected = False
    log.warning("MQTT disconnected rc=%s", rc)
    print(f"[MQTT] Disconnected rc={rc} — reconnecting ...")


def on_message(client, userdata, msg):
    """
    Receives:
      ols/io/output/{name}        "1" or "0"  → set physical output
      ols/io/sim/input/{name}     "1" or "0"  → inject simulated input (sim mode only)
    """
    topic   = msg.topic
    payload = msg.payload.decode().strip()
    value   = 1 if payload in ("1", "true", "True", "on", "ON") else 0

    if topic.startswith(f"{T_OUTPUT}/"):
        name = topic[len(T_OUTPUT)+1:]
        if name in OUTPUT_PINS:
            with _lock:
                _output_state[name] = value
            _hal_write_output(name, value)
            log.debug("Output set: %s = %d", name, value)
        else:
            log.warning("Unknown output name: %s", name)

    elif topic.startswith("ols/io/sim/input/") and _HW == "sim":
        name = topic.split("/")[-1]
        _sim_set_input(name, value)
        log.debug("[SIM] Input injected: %s = %d", name, value)


# ══════════════════════════════════════════════════════════════════
#  INPUT POLLING THREAD
#  Scans inputs at POLL_HZ, publishes on every rising/falling edge.
#  Also publishes a full JSON snapshot at 1 Hz.
# ══════════════════════════════════════════════════════════════════
def _input_poll_thread():
    global _input_state
    last_snapshot = 0.0

    log.info("Input polling thread started at %d Hz.", POLL_HZ)

    while True:
        time.sleep(POLL_SLEEP)

        new_states = _hal_read_all_inputs()
        edges      = _detect_edges(new_states)

        # Publish individual changes
        for name, old_val, new_val in edges:
            log.info("INPUT EDGE  %-28s  %d → %d", name, old_val, new_val)
            if _mqtt_connected:
                _mqtt_client.publish(f"{T_INPUT}/{name}", str(new_val), retain=True)

        # Update shared state
        if edges:
            with _lock:
                _input_state.update(new_states)

        # Publish full snapshot at 1 Hz
        now = time.time()
        if now - last_snapshot >= 1.0:
            last_snapshot = now
            if _mqtt_connected:
                with _lock:
                    snap = dict(_input_state)
                _mqtt_client.publish(T_INPUTS, json.dumps(snap), retain=False)


# ══════════════════════════════════════════════════════════════════
#  STATUS HEARTBEAT THREAD  (1 Hz)
# ══════════════════════════════════════════════════════════════════
def _heartbeat_thread():
    while True:
        time.sleep(1)
        if _mqtt_connected:
            with _lock:
                out_snap = dict(_output_state)
            payload = json.dumps({
                "ts":      time.strftime("%Y-%m-%dT%H:%M:%S"),
                "hw":      _HW,
                "poll_hz": POLL_HZ,
                "outputs": out_snap,
            })
            _mqtt_client.publish(T_STATUS, payload, retain=False)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def main():
    global _mqtt_client

    print("=" * 60)
    print("  OLS I/O Interface")
    print(f"  Hardware  : {_HW.upper()}")
    print(f"  Inputs    : {len(INPUT_PINS)}")
    print(f"  Outputs   : {len(OUTPUT_PINS)}")
    print(f"  Broker    : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Poll rate : {POLL_HZ} Hz")
    print("=" * 60)

    # Build MQTT client
    _mqtt_client = mqtt.Client(client_id="ols-io-interface", clean_session=True)
    if MQTT_USER:
        _mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
    _mqtt_client.on_connect    = on_connect
    _mqtt_client.on_disconnect = on_disconnect
    _mqtt_client.on_message    = on_message
    _mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)

    # Start background threads
    threading.Thread(target=_input_poll_thread, daemon=True, name="io-poll").start()
    threading.Thread(target=_heartbeat_thread,  daemon=True, name="io-hb"  ).start()

    # Connect and block
    while True:
        try:
            print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
            _mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            _mqtt_client.loop_forever()
        except Exception as exc:
            log.error("MQTT fatal: %s — retry in 5 s", exc)
            print(f"[MQTT] Error: {exc} — retrying in 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()