# InfluxDB query functions for the IPAR40TK server dashboard
# This module provides functions to query the InfluxDB time-series database for machine telemetry, features, predictions and status information. 
# The functions use the InfluxDB Python client to execute Flux queries and return the results as pandas DataFrames for further processing and visualization in the dashboard.

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

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        if len(df) == 0:
            return pd.DataFrame()
        df = pd.concat(df)

    if df is None or df.empty:
        return pd.DataFrame()

    return df

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

    if df.empty:
        return None

    return df

def query_anomaly_stats(machine, aspect):
    query = f'''
    from(bucket:"openmaps")
      |> range(start:-1h)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_predictions")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
      |> filter(fn:(r)=> r["aspect"]=="{aspect}")
    '''
    
    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = pd.concat(df)

    if df.empty:
        return None, None

    values = df["_value"].values

    return float(values.mean()), float(values.std())

def query_fft(machine, axis):

    query = f'''
    from(bucket:"openmaps")
      |> range(start:-10m)
      |> filter(fn:(r)=> r["_measurement"]=="lathe_fft")
      |> filter(fn:(r)=> r["machine"]=="{machine}")
      |> filter(fn:(r)=> r["axis"]=="{axis}")
      |> group(columns: ["freq"])
      |> last()
    '''

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = pd.concat(df)

    if df.empty:
        return None

    return df

def query_status(machine):

    query = f'''
    from(bucket:"openmaps")
      |> range(start:-5m)
      |> filter(fn: (r) => r["_measurement"] == "lathe_status_esp1" or r["_measurement"] == "lathe_status_esp2")
      |> filter(fn: (r) => r["_field"] == "esp1" or r["_field"] == "esp2" or r["_field"] == "esp2_collect" or r["_field"] == "esp2_mpu" or r["_field"] == "mpu" or r["_field"] == "mqtt" or r["_field"] == "temp" or r["_field"] == "rpm")
      |> filter(fn: (r) => r["machine"] == "{machine}")
    '''

    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        if len(df) == 0:
            return None
        df = pd.concat(df)

    if df.empty:
        return None

    return df

def query_home_export_data(machine: str, days: int):

    query = f'''
    from(bucket: "openmaps")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "lathe_features")
      |> filter(fn: (r) => r.machine == "{machine}")
      |> pivot(
            rowKey:["_time"],
            columnKey:["_field"],
            valueColumn:"_value"
        )
      |> keep(columns: [
            "_time",
            "current_mean",
            "current_imbalance",
            "rpm",
            "tempC",
            "vibX_rms",
            "vibY_rms",
            "vibZ_rms",
            "vibX_fft_peak",
            "vibY_fft_peak",
            "vibZ_fft_peak"
        ])
    '''

    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        result = pd.concat(result, ignore_index=True)

    return result

def query_vibration_export_data(machine: str, days: int):

    query = f'''
    from(bucket: "openmaps")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "lathe_features")
      |> filter(fn: (r) => r.machine == "{machine}")
      |> pivot(
            rowKey:["_time"],
            columnKey:["_field"],
            valueColumn:"_value"
        )
      |> keep(columns: [
            "_time",
            "vibX_rms",
            "vibY_rms",
            "vibZ_rms",
            "vibX_fft_peak",
            "vibY_fft_peak",
            "vibZ_fft_peak",
            "vibX_psd_peak",
            "vibY_psd_peak",
            "vibZ_psd_peak"
        ])
    '''

    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        result = pd.concat(result, ignore_index=True)

    return result