import dash
from dash import dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/anomalies")

layout = dbc.Container([

    dcc.Graph(id="anomaly-timeline")

])