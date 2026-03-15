import json
import paho.mqtt.client as mqtt
import os

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

client = mqtt.Client()

if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASS)

client.connect(MQTT_BROKER, MQTT_PORT)

def publish(topic, value):

    # convert list/dict to JSON
    if isinstance(value, (list, dict)):
        value = json.dumps(value)

    client.publish(topic, value)