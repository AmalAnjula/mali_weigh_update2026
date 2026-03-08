#!/usr/bin/env python3
"""
io_handler.py  —  IO input subscriber for app.py
=================================================
Import this module from app.py and call  start(mqtt_client)  after
the MQTT client is connected.

It subscribes to  ols/io/input/#  topics published by io_interface.py
and maps them to the same logic that UI button clicks trigger.

Also publishes output commands to  ols/io/output/{name}  whenever
app state changes (valve open/close, alarms, LEDs, solenoids).

Usage in app.py:
    import io_handler
    # inside on_connect callback, after client.subscribe(MQTT_TOPIC):
    io_handler.start(client, state, _lock, tech_log)
"""

import json, threading, time

# ── Output topic root ──────────────────────────────────────────────
T_OUT = "ols/io/output"

# ── Debounce time for physical buttons (seconds) ──────────────────
DEBOUNCE_S = 0.05   # 50 ms

# ── Shared references (set by start()) ────────────────────────────
_client    = None
_state     = None
_lock      = None
_log       = None

# Last time each input fired (for debounce)
_last_fire: dict[str, float] = {}


# ══════════════════════════════════════════════════════════════════
#  OUTPUT HELPERS  — publish to io_interface.py
# ══════════════════════════════════════════════════════════════════
def set_output(name: str, value: int):
    """Publish  ols/io/output/{name}  "1" or "0" ."""
    if _client:
        _client.publish(f"{T_OUT}/{name}", str(value), retain=False)


def sync_outputs():
    """
    Read current app state and push all relevant outputs.
    Call this after any state change (valve open, alarm, etc.)
    """
    if not _state or not _client:
        return

    with _lock:
        infeed_valve   = int(_state["infeed"]["valve_open"])
        outfeed_valve  = int(_state["outfeed"]["valve_open"])
        hi_alarm       = int(_state["tank"]["hi_alarm"])
        lo_alarm       = int(_state["tank"]["lo_alarm"])
        infeed_run     = int(_state["infeed"]["running"])
        outfeed_run    = int(_state["outfeed"]["running"])

    # Solenoids follow valve state
    set_output("input_solenoid",  infeed_valve)
    set_output("output_solenoid", outfeed_valve)

    # Relay follows either side running
    set_output("relay", int(infeed_run or outfeed_run))

    # Indicator LEDs
    set_output("indicator_led_in",  infeed_run)
    set_output("indicator_led_out", outfeed_run)

    # Alarm LED — hi or lo alarm
    set_output("alarm_led", int(hi_alarm or lo_alarm))

    # Power LED always on (driven by app being alive)
    set_output("power_led", 1)


# ══════════════════════════════════════════════════════════════════
#  INPUT MAP
#  Maps each physical input name → handler function (rising edge)
# ══════════════════════════════════════════════════════════════════
def _handle_infeed_auto(rising: bool):
    """Physical infeed AUTO button pressed."""
    if not rising:
        return
    _log.info("[IO] infeed_auto button — setting AUTO mode")
    with _lock:
        _state["infeed"]["mode"] = "AUTO"
    _client.publish("ols/io/status/infeed_mode", "AUTO", retain=True)


def _handle_infeed_start(rising: bool):
    """Physical infeed START button pressed."""
    if not rising:
        return
    _log.info("[IO] infeed_start button — triggering infeed start")
    # Simulate the same API call as the UI button
    # We post to the internal control bus by calling the shared state directly
    # The main app's api_control handles thread spawning
    _client.publish("ols/io/cmd/control",
                    json.dumps({"side": "infeed", "action": "run", "value": "START"}))


def _handle_infeed_stop(rising: bool):
    if not rising:
        return
    _log.info("[IO] infeed_stop button — triggering infeed stop")
    _client.publish("ols/io/cmd/control",
                    json.dumps({"side": "infeed", "action": "run", "value": "STOP"}))


def _handle_outfeed_auto(rising: bool):
    if not rising:
        return
    _log.info("[IO] outfeed_auto button — setting AUTO mode")
    with _lock:
        _state["outfeed"]["mode"] = "AUTO"


def _handle_outfeed_start(rising: bool):
    if not rising:
        return
    _log.info("[IO] outfeed_start button — triggering outfeed start")
    _client.publish("ols/io/cmd/control",
                    json.dumps({"side": "outfeed", "action": "run", "value": "START"}))


def _handle_outfeed_stop(rising: bool):
    if not rising:
        return
    _log.info("[IO] outfeed_stop button — triggering outfeed stop")
    _client.publish("ols/io/cmd/control",
                    json.dumps({"side": "outfeed", "action": "run", "value": "STOP"}))


def _handle_low_level_sensor(rising: bool):
    """Physical low level float switch."""
    import app as _app    # import lazily to avoid circular import
    _app.low_level_sensor = rising
    _log.info("[IO] low_level_sensor -> %d", int(rising))
    with _lock:
        _state["tank"]["lo_alarm"] = rising
    set_output("alarm_led", int(rising))


def _handle_hi_level_sensor(rising: bool):
    import app as _app
    _log.info("[IO] hi_level_sensor -> %d", int(rising))
    with _lock:
        _state["tank"]["hi_alarm"] = rising
    set_output("alarm_led", int(rising))


def _handle_invalve_open(rising: bool):
    _log.debug("[IO] invalve_open feedback -> %d", int(rising))
    set_output("indicator_led_in", int(rising))


def _handle_invalve_close(rising: bool):
    _log.debug("[IO] invalve_close feedback -> %d", int(rising))


def _handle_outvalve_open(rising: bool):
    _log.debug("[IO] outvalve_open feedback -> %d", int(rising))
    set_output("indicator_led_out", int(rising))


def _handle_outvalve_close(rising: bool):
    _log.debug("[IO] outvalve_close feedback -> %d", int(rising))


def _handle_lock_button(rising: bool):
    if not rising:
        return
    _log.info("[IO] lock_button pressed")
    # TODO: implement panel lock logic
    set_output("alarm_led", 1)
    time.sleep(0.2)
    set_output("alarm_led", 0)


def _handle_power_pin(rising: bool):
    _log.info("[IO] power_pin -> %d", int(rising))
    set_output("power_led", int(rising))


# ── Dispatch table: input name → handler ───────────────────────────
_INPUT_HANDLERS = {
    "infeed_auto":      _handle_infeed_auto,
    "infeed_start":     _handle_infeed_start,
    "infeed_stop":      _handle_infeed_stop,
    "outfeed_auto":     _handle_outfeed_auto,
    "outfeed_start":    _handle_outfeed_start,
    "outfeed_stop":     _handle_outfeed_stop,
    "low_level_sensor": _handle_low_level_sensor,
    "hi_level_sensor":  _handle_hi_level_sensor,
    "invalve_open":     _handle_invalve_open,
    "invalve_close":    _handle_invalve_close,
    "outvalve_open":    _handle_outvalve_open,
    "outvalve_close":   _handle_outvalve_close,
    "lock_button":      _handle_lock_button,
    "power_pin":        _handle_power_pin,
}


# ══════════════════════════════════════════════════════════════════
#  WAITING LED THREAD
#  Blinks in_waiting_led  while busyFlagOutfeedBusy is set.
#  Blinks out_waiting_led while busyFlagInfeedBusy is set.
# ══════════════════════════════════════════════════════════════════
def _waiting_led_thread():
    import app as _app
    _blink = False
    while True:
        time.sleep(0.5)
        _blink = not _blink

        # Infeed waiting = outfeed is busy and infeed is waiting for it
        set_output("in_waiting_led",  int(_app.busyFlagOutfeedBusy and _blink))
        # Outfeed waiting = infeed is busy and outfeed is waiting for it
        set_output("out_waiting_led", int(_app.busyFlagInfeedBusy  and _blink))


# ══════════════════════════════════════════════════════════════════
#  MQTT MESSAGE HANDLER  (registered on app.py's existing client)
# ══════════════════════════════════════════════════════════════════
def _on_io_message(client, userdata, msg):
    """Receives  ols/io/input/{name}  from io_interface.py."""
    topic   = msg.topic
    payload = msg.payload.decode().strip()
    value   = 1 if payload in ("1", "true", "True") else 0

    prefix = "ols/io/input/"
    if not topic.startswith(prefix):
        return

    name = topic[len(prefix):]

    # Debounce
    now = time.time()
    if now - _last_fire.get(name, 0) < DEBOUNCE_S:
        return
    _last_fire[name] = now

    handler = _INPUT_HANDLERS.get(name)
    if handler:
        rising = bool(value)
        try:
            handler(rising)
        except Exception as exc:
            _log.error("IO handler error [%s]: %s", name, exc)
    else:
        _log.debug("[IO] No handler for input: %s = %d", name, value)


# ══════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════
def start(mqtt_client, shared_state: dict, lock: object, logger):
    """
    Call this from app.py after MQTT connects.

    Example in app.py's on_connect():
        import io_handler
        io_handler.start(client, state, _lock, tech_log)
    """
    global _client, _state, _lock, _log
    _client = mqtt_client
    _state  = shared_state
    _lock   = lock
    _log    = logger

    # Subscribe to IO input events
    mqtt_client.subscribe("ols/io/input/#")
    mqtt_client.message_callback_add("ols/io/input/#", _on_io_message)

    # Start the waiting LED blink thread
    threading.Thread(target=_waiting_led_thread, daemon=True,
                     name="io-wait-led").start()

    # Initial output sync
    sync_outputs()
    set_output("power_led", 1)

    logger.info("[IO handler] Started. Subscribed to ols/io/input/#")
    print("[io_handler] Started — listening for physical I/O events.")