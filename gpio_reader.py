from gpiozero import OutputDevice, InputDevice
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device

# ── RPi5: use lgpio pin factory (required for Raspberry Pi 5) ─────
Device.pin_factory = LGPIOFactory()


# ── Output pin definitions ─────────────────────────────────────────
timer_pin      = 25
in_wei_led     = 15
out_wei_led    = 18
# ⚠️  WARNING: myrelay was pin 12, but pin 12 is also used by
#     relay_normal_off_pin (INPUT). Assign myrelay a unique pin!
myrelay        = 4 #12   # <-- CHANGE THIS to an unused pin
alm_led        = 1
pwr_led        = 14
out_solv       = 23
in_solv        = 24
ind_led_in     = 7
ind_led_out    = 8
b_led          = 20

# ── Input pin definitions ──────────────────────────────────────────
val_down_pin         = 27
val_up_pin           = 17
lowr_sns_pin         = 10
up_sns_pin           = 22
intke_remot_pin      = 26   # renamed from intke_mode_pin (matched gpiotest.py)
intke_start_pin      = 13
intke_stop_pin       = 19
lock_btn_pin         = 21
outtk_start_pin      = 11
outtk_stop_pin       = 5
outk_remot_pin       = 6
relay_normal_off_pin = 12
pwr_pin              = 16


# ── Initialise output devices (start LOW / inactive) ──────────────
OUTPUT_PINS = {
    "timer":       timer_pin,
    "in_wei_led":  in_wei_led,
    "out_wei_led": out_wei_led,
    "myrelay":     myrelay,
    "alm_led":     alm_led,
    "pwr_led":     pwr_led,
    "out_solv":    out_solv,
    "in_solv":     in_solv,
    "ind_led_in":  ind_led_in,
    "ind_led_out": ind_led_out,
    "b_led":       b_led,
}

# ── Initialise input devices (pull_up=False → internal pull-down) ──
INPUT_PINS = {
    "val_down":         val_down_pin,
    "val_up":           val_up_pin,
    "lowr_sns":         lowr_sns_pin,
    "up_sns":           up_sns_pin,
    "intke_remot":      intke_remot_pin,   # renamed from "intake_mode"
    "intke_start":      intke_start_pin,
    "intke_stop":       intke_stop_pin,
    "lock_btn":         lock_btn_pin,
    "outtk_start":      outtk_start_pin,
    "outtk_stop":       outtk_stop_pin,
    "outk_remot":       outk_remot_pin,
    "relay_normal_off": relay_normal_off_pin,
    "pwr":              pwr_pin,
}

# ── Build gpiozero device objects ──────────────────────────────────
# InputDevice(pin, pull_up=False) → equivalent to GPIO.PUD_DOWN
_input_devices:  dict[str, InputDevice]  = {
    name: InputDevice(pin, pull_up=False)
    for name, pin in INPUT_PINS.items()
}

# OutputDevice(pin, initial_value=False) → starts LOW
_output_devices: dict[str, OutputDevice] = {
    name: OutputDevice(pin, initial_value=False)
    for name, pin in OUTPUT_PINS.items()
}

# ── Previous / current state — used for edge detection ────────────
_prev: dict[str, int] = {name: 0 for name in INPUT_PINS}
_curr: dict[str, int] = {name: 0 for name in INPUT_PINS}


# ══════════════════════════════════════════════════════════════════
#  CALL THIS ONCE PER POLL LOOP — updates curr and prev
# ══════════════════════════════════════════════════════════════════
def update():
    """Read all input pins. Must be called once at the top of every poll cycle."""
    global _prev, _curr
    _prev = dict(_curr)
    _curr = {name: int(dev.value) for name, dev in _input_devices.items()}


# ══════════════════════════════════════════════════════════════════
#  EDGE HELPERS  (only valid after update() is called)
# ══════════════════════════════════════════════════════════════════
def rising(name: str) -> bool:
    """True only on 0 → 1 transition (button just pressed)."""
    return bool(_curr[name]) and not bool(_prev[name])

def falling(name: str) -> bool:
    """True only on 1 → 0 transition (button just released)."""
    return not bool(_curr[name]) and bool(_prev[name])

def state(name: str) -> int:
    """Current raw value of an input pin (0 or 1)."""
    return _curr[name]

def changed(name: str) -> bool:
    """True if pin value is different from last cycle."""
    return _curr[name] != _prev[name]


# ══════════════════════════════════════════════════════════════════
#  CONVENIENCE
# ══════════════════════════════════════════════════════════════════
def read_inputs() -> dict:
    """Return a copy of the current input state snapshot."""
    return dict(_curr)

def read_pin(name: str) -> int:
    """Read a single input pin live (bypasses snapshot)."""
    dev = _input_devices.get(name)
    if dev is None:
        raise ValueError(f"Unknown input pin name: {name}")
    return int(dev.value)


def set_output(name: str, value: int):
    """Set an output pin to 1 (on) or 0 (off)."""
    dev = _output_devices.get(name)
    if dev is None:
        raise ValueError(f"Unknown output pin: {name}")
    dev.on() if value else dev.off()


def output_on(name: str):
    """Drive an output pin HIGH."""
    dev = _output_devices.get(name)
    if dev is None:
        raise ValueError(f"Unknown output pin: {name}")
    dev.on()


def output_off(name: str):
    """Drive an output pin LOW."""
    dev = _output_devices.get(name)
    if dev is None:
        raise ValueError(f"Unknown output pin: {name}")
    dev.off()


def toggle_output(name: str):
    """Toggle an output pin between HIGH and LOW."""
    dev = _output_devices.get(name)
    if dev is None:
        raise ValueError(f"Unknown output pin: {name}")
    dev.toggle()