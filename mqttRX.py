import time

import paho.mqtt.client as mqtt_client
import os


MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT",  "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC",  "serial/weight")
MQTT_USER   = os.getenv("MQTT_USER",   "")          # leave "" if no auth
MQTT_PASS   = os.getenv("MQTT_PASS",   "")



try:
    import paho.mqtt.client as mqtt_client
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("  paho-mqtt not installed - MQTT thread disabled.")
    print("   Install with:  pip install paho-mqtt")


# ══════════════════════════════════════════════════════════════════
#  MQTT CALLBACKS  (run inside paho's network thread)
# ══════════════════════════════════════════════════════════════════
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        
    else:
        print(f"\n[MQTT] Connection failed  rc={rc}")
        

def on_disconnect(client, userdata, rc):
    
    print(f"\n[MQTT] Disconnected (rc={rc}) — paho will auto-reconnect")


def on_message_weight(client, userdata, msg):
    """
    Your original callback — unchanged logic.
    Parses weiVal, sets serial_error, and syncs into shared state.
    """
    global weiVal, serial_error

    payload_str = msg.payload.decode()
    print(f"\n[MQTT] Received message on {msg.topic}: {payload_str}")
          
        


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
            
            print(f"[MQTT] Error: {exc} — retrying in 5 s")
           
            time.sleep(5)



_mqtt_thread()