import dash
from dash import dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/about")

layout = dbc.Container([

    dcc.Markdown("""

# OpenMAPS

Industrial IoT monitoring platform.

Features:

• MQTT telemetry  
• InfluxDB time series storage  
• Online anomaly detection  
• Predictive maintenance dashboard  

""")

])