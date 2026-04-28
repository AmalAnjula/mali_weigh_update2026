# publisher.py
import paho.mqtt.client as mqtt
import json, time

BROKER = "localhost"   # RPi 1's own IP
TOPIC  = "sensors/data"

client = mqtt.Client()
client.connect(BROKER, 1883)

while True:
    payload = {
        "temperature": 36.5,
        "humidity":    62,
        "pressure":    1013
    }
    client.publish(TOPIC, json.dumps(payload))
    print("Sent:", payload)
    time.sleep(2)