import time

import serial
import paho.mqtt.client as mqtt
import re
import yaml


last_weight = None          # track previous accepted value
SPIKE_LIMIT = 1.0 
buffer      = ""
with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)


serial_port = CONFIG["serial"]["port"]
serial_baud = CONFIG["serial"]["baudrate"]
 
ser = serial.Serial(serial_port,serial_baud)

SPIKE_LIMIT = CONFIG["serial"]["diff"]

client = mqtt.Client()
client.connect("localhost",1883)

print("OK")
while True:
    
    try:
        
        chunk = ser.read(16).decode('utf-8', errors='ignore')
        buffer += chunk

        numbers = re.findall(r'=\s*([\d.]+)', buffer)
        buffer = re.split(r'=\s*[\d.]+', buffer)[-1]  # keep partial tail

        for raw in numbers:
            weight = float(raw)

            # ── Spike filter ──────────────────────────────────────
            if last_weight is not None:
                diff = abs(weight - last_weight)
                if diff > SPIKE_LIMIT:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> IGNORED spike: "
                        f"prev={last_weight:.2f}  new={weight:.2f}  diff={diff:.2f}")
                    continue          # skip, keep last_weight unchanged
            # ─────────────────────────────────────────────────────

            last_weight = weight
                
            client.publish("serial/weight", weight,qos=0,retain=False)
            print(time.strftime("%Y-%m-%d %H:%M:%S") + " >> :", weight)         
            
        
    except Exception as e:
        client.publish("serial/weight", "#"+str(e))
        print("Error reading from serial or publishing to MQTT:", str(e))
        time.sleep(10)  # Wait before retrying
        continue


         