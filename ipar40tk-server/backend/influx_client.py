from influxdb_client import InfluxDBClient, Point
from config import *

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api()

# Write transformed data.
def write_feature(machine, feature_name, value):

    point = (
        Point("lathe_features")
        .tag("machine", machine)
        .field(feature_name, float(value))
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)

# Write anomaly preditions by aspect.
def write_prediction(machine, aspect, score):

    point = (
        Point("lathe_predictions")
        .tag("machine", machine)
        .tag("aspect", aspect)
        .field("anomaly_score", float(score))
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)