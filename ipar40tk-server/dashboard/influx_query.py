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

    query = f'''
    from(bucket:"openmaps")
      |> range(start:-10m)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_features")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
    '''

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        if len(df) == 0:
            return pd.DataFrame()
        df = pd.concat(df)

    if df is None or df.empty:
        return pd.DataFrame()

    return df


def query_anomalies(machine):

    query=f'''
    from(bucket:"openmaps")
      |> range(start:-1h)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_predictions")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
    '''

    return query_api.query_data_frame(query)

def query_latest_anomaly(machine, aspect):

    query = f'''
    from(bucket:"openmaps")
      |> range(start:-10m)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_predictions")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
      |> filter(fn:(r)=> r["aspect"]=="{aspect}")
      |> last()
    '''

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = pd.concat(df)

    if df.empty:
        return None

    return float(df["_value"].iloc[-1])

def query_vibration(machine, axis):

    query = f'''
    from(bucket:"openmaps")
      |> range(start:-10m)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_features")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
      |> filter(fn:(r)=> r["_field"]=="{axis}")
    '''

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = pd.concat(df)

    return df