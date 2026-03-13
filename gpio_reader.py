import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

 

# ── Output pin definitions ─────────────────────────────────────────
timer_pin      = 25
in_wei_led     = 15
out_wei_led    = 18
myrelay        = 12
alm_led        = 1
pwr_led        = 14
out_solv       = 23
in_solv        = 24
ind_led_in     = 7
ind_led_out    = 8
b_led          = 20

# ── Pin definitions ────────────────────────────────────────────────
val_down_pin         = 27
val_up_pin           = 17
lowr_sns_pin         = 10
up_sns_pin           = 22
intke_mode_pin      = 26
intke_start_pin      = 13
intke_stop_pin       = 19
lock_btn_pin         = 21
outtk_start_pin      = 11
outtk_stop_pin       = 5
outk_remot_pin       = 6
relay_normal_off_pin = 12
pwr_pin              = 16

OUTPUT_PINS = {
    "timer": timer_pin,
    "in_wei_led": in_wei_led,
    "out_wei_led": out_wei_led,
    "myrelay": myrelay,
    "alm_led": alm_led,
    "pwr_led": pwr_led,
    "out_solv": out_solv,
    "in_solv": in_solv,
    "ind_led_in": ind_led_in,
    "ind_led_out": ind_led_out,
    "b_led": b_led,
}

# ── Pin map ────────────────────────────────────────────────────────
INPUT_PINS = {
    "val_down":         val_down_pin,
    "val_up":           val_up_pin,
    "lowr_sns":         lowr_sns_pin,
    "up_sns":           up_sns_pin,
    "intake_mode":      intke_mode_pin,
    "intke_start":      intke_start_pin,
    "intke_stop":       intke_stop_pin,
    "lock_btn":         lock_btn_pin,
    "outtk_start":      outtk_start_pin,
    "outtk_stop":       outtk_stop_pin,
    "outk_remot":       outk_remot_pin,
    "relay_normal_off": relay_normal_off_pin,
    "pwr":              pwr_pin,
}

for pin in INPUT_PINS.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

for pin in OUTPUT_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ── Previous / current state — used for edge detection ────────────
_prev: dict[str, int] = {name: 0 for name in INPUT_PINS}
_curr: dict[str, int] = {name: 0 for name in INPUT_PINS}


# ══════════════════════════════════════════════════════════════════
#  CALL THIS ONCE PER POLL LOOP — updates curr and prev
# ══════════════════════════════════════════════════════════════════
def update():
    """Read all pins. Must be called once at the top of every poll cycle."""
    global _prev, _curr
    _prev = dict(_curr)
    _curr = {name: GPIO.input(pin) for name, pin in INPUT_PINS.items()}


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
    """Current raw value of a pin (0 or 1)."""
    return _curr[name]

def changed(name: str) -> bool:
    """True if pin value is different from last cycle."""
    return _curr[name] != _prev[name]


# ══════════════════════════════════════════════════════════════════
#  CONVENIENCE
# ══════════════════════════════════════════════════════════════════
def read_inputs() -> dict:
    return dict(_curr)

def read_pin(name: str) -> int:
    pin = INPUT_PINS.get(name)
    if pin is None:
        raise ValueError(f"Unknown pin name: {name}")
    return GPIO.input(pin)


def set_output(name: str, value: int):
    pin = OUTPUT_PINS.get(name)
    if pin is None:
        raise ValueError(f"Unknown output pin: {name}")
    GPIO.output(pin, value)


def output_on(name: str):
    set_output(name, 1)


def output_off(name: str):
    set_output(name, 0)


def toggle_output(name: str):
    pin = OUTPUT_PINS.get(name)
    if pin is None:
        raise ValueError(f"Unknown output pin: {name}")
    GPIO.output(pin, not GPIO.input(pin))
    