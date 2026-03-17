from influxdb_client import InfluxDBClient
import pandas as pd
from config import *

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

query_api = client.query_api()


def query_features(machine):

    query=f'''
    from(bucket:"openmaps")
      |> range(start:-10m)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_features")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
    '''

    return query_api.query_data_frame(query)


def query_anomalies(machine):

    query=f'''
    from(bucket:"openmaps")
      |> range(start:-1h)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_predictions")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
    '''

    return query_api.query_data_frame(query)