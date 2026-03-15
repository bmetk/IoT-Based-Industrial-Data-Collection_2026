import paho.mqtt.client as mqtt
from feature_engineering import process_message
from config import *


def on_connect(client, userdata, flags, rc):

    print("MQTT connected")

    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):

    topic = msg.topic

    payload = msg.payload.decode()

    process_message(topic, payload)


def start():

    client = mqtt.Client()

    client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT)

    client.loop_forever()