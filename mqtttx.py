import time
import logging
from logging.handlers import TimedRotatingFileHandler

import serial
import paho.mqtt.client as mqtt
import re
import yaml



 
# ── Logging setup ─────────────────────────────────────────────────────────────
handler = TimedRotatingFileHandler(
    filename="weight.log",
    when="midnight",        # rotate once per day at midnight
    interval=1,
    backupCount=3,          # keep today + 3 previous days, older files are deleted
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s >> %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[handler])
# ─────────────────────────────────────────────────────────────────────────────


last_weight = None          # track previous accepted value
SPIKE_LIMIT = 1.0
buffer      = ""

with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)

serial_port = CONFIG["serial"]["port"]
serial_baud = CONFIG["serial"]["baudrate"]

ser = serial.Serial(serial_port, serial_baud)

SPIKE_LIMIT = CONFIG["serial"]["diff"]

client = mqtt.Client()
client.connect("localhost", 1883)

print("OK")
clear_now = False

while True:
    try:
        chunk  = ser.read(20).decode('utf-8', errors='ignore')
        buffer += chunk

        numbers = re.findall(r'=\s*([\d.]+)', buffer)
        buffer  = re.split(r'=\s*[\d.]+', buffer)[-1]  # keep partial tail

        for raw in numbers:
            weight = float(raw)

            # ── Spike filter ──────────────────────────────────────
            if last_weight is not None:
                diff = abs(weight - last_weight)
                if diff > SPIKE_LIMIT:
                    msg = (f"IGNORED spike: prev={last_weight:.2f}  "
                           f"new={weight:.2f}  diff={diff:.2f}")
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> {msg}")
                    logging.warning(msg)
                    continue          # skip, keep last_weight unchanged

            if clear_now:
                logging.info("Clearing spike filter after previous spike")
            # ─────────────────────────────────────────────────────

            last_weight = weight

            client.publish("serial/weight", weight, qos=0, retain=False)
            log_msg = f"Weight published: {weight}"
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> : {weight}")
            #logging.info(log_msg)

    except Exception as e:
        err_msg = f"Error reading from serial or publishing to MQTT: {e}"
        client.publish("serial/weight", "#" + str(e))
        print(err_msg)
        logging.error(err_msg)
        time.sleep(10)
        continue