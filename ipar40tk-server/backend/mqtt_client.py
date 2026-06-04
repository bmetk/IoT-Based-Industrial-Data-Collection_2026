# MQTT client module for the IPAR40TK server backend
# Handles connection to the MQTT broker, subscription to telemetry topics, and processing of incoming messages using the feature engineering and ML model components

import paho.mqtt.client as mqtt
from feature_engineering import process_message
from config import *
from ml_model import load_baselines, load_training_data, train_state_classifier, set_state_clf


def on_connect(client, userdata, flags, rc):

    print("MQTT connected")

    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):

    topic = msg.topic

    payload = msg.payload.decode()

    process_message(topic, payload)


def start():
    print("[INIT] Loading ML baselines...")
    load_baselines("/app/baselines")
    print("[INIT] Training state classifier...")
    df = load_training_data("/app/baselines")
    state_clf = train_state_classifier(df)
    set_state_clf(state_clf)
    client = mqtt.Client()

    client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT)

    client.loop_forever()