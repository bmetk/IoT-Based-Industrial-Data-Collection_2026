import json
import paho.mqtt.client as mqtt
import os
import threading

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

client = mqtt.Client()
mqtt_lock = threading.Lock()

if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASS)

client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

def publish(topic, value):
    with mqtt_lock:
        value = json.dumps(value)
        client.publish(topic, value)

def publish_vibration(topic, signal):

    with mqtt_lock:
        client.publish(
            topic,
            json.dumps(signal)
        )