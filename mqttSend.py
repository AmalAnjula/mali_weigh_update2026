import queue
import threading

# -----------------------------------------------------------
# Publish queue  (put items from anywhere in your code)
# -----------------------------------------------------------
_publish_queue = queue.Queue()

def mqtt_publish(topic: str, payload, retain: bool = False, qos: int = 0):
    """
    Thread-safe helper — call this from anywhere to queue a publish.
    """
    _publish_queue.put((topic, str(payload), qos, retain))


# -----------------------------------------------------------
# Publisher thread
# -----------------------------------------------------------
def _mqtt_publish_thread():
    """
    Daemon thread that drains _publish_queue and publishes
    only when the broker is connected.
    """
    if not MQTT_AVAILABLE:
        print("[MQTT-PUB] Thread not started — paho-mqtt not installed.")
        return

    pub_client = mqtt_client.Client(client_id="ols-publisher", clean_session=True)

    if MQTT_USER:
        pub_client.username_pw_set(MQTT_USER, MQTT_PASS)

    pub_client.reconnect_delay_set(min_delay=1, max_delay=30)

    # Keep trying to connect in the background
    while True:
        try:
            print(f"[MQTT-PUB] Connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
            pub_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            pub_client.loop_start()          # non-blocking — lets us drain the queue

            while True:
                try:
                    topic, payload, qos, retain = _publish_queue.get(timeout=1)
                    result = pub_client.publish(topic, payload, qos=qos, retain=retain)
                    if result.rc != mqtt_client.MQTT_ERR_SUCCESS:
                        tech_log.warning("[MQTT-PUB] Publish failed rc=%s  topic=%s", result.rc, topic)
                    else:
                        print(f"[MQTT-PUB] → {topic} : {payload}")
                    _publish_queue.task_done()
                except queue.Empty:
                    # Nothing to send — check connection is still alive
                    if not pub_client.is_connected():
                        print("[MQTT-PUB] Lost connection — reconnecting …")
                        break

        except Exception as exc:
            tech_log.error("[MQTT-PUB] Fatal: %s — retry in 5 s", exc)
            print(f"[MQTT-PUB] Error: {exc} — retrying in 5 s")
        finally:
            try:
                pub_client.loop_stop()
            except Exception:
                pass

        time.sleep(5)


# -----------------------------------------------------------
# Start both threads (add alongside your existing subscriber)
# -----------------------------------------------------------
threading.Thread(target=_mqtt_thread,         daemon=True, name="mqtt-sub").start()
threading.Thread(target=_mqtt_publish_thread, daemon=True, name="mqtt-pub").start()