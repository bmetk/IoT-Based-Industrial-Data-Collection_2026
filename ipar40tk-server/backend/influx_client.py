from influxdb_client import InfluxDBClient, Point
from config import *

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api()

# Functions to write features and predictions to InfluxDB
def write_feature(machine, feature_name, value):

    point = (
        Point("lathe_features")
        .tag("machine", machine)
        .field(feature_name, float(value))
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)

# Function to write anomaly scores to InfluxDB
def write_prediction(machine, score):

    point = (
        Point("lathe_predictions")
        .tag("machine", machine)
        .field("anomaly_score", float(score))
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)