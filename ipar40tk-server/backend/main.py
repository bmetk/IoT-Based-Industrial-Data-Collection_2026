# Main entry point for the IPAR40TK server backend |Calls start function from mqtt_client module to initialize the MQTT client and start processing incoming telemetry data

from mqtt_client import start

if __name__ == "__main__":

    print("Starting analytics backend")

    start()