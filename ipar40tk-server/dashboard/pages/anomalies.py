import dash
from dash import dcc, Input, Output, no_update
import dash_bootstrap_components as dbc
from influx_query import *
import plotly.graph_objects as go
import pandas as pd

dash.register_page(__name__, path="/anomalies")

layout = dbc.Container([

    dbc.Row([
        dbc.Col([
            dcc.Graph(id="anomaly-timeline")
        ])
    ])
    
])
@dash.callback(
    Output("anomaly-timeline","figure"),

    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_anomaly(machine,_):
    df = query_anomalies(machine)

    if df is None or df.empty:
        return go.Figure()
    
    if isinstance(df, list):
        df = pd.concat(df)

    df = df.sort_values("_time")

    x = df["_time"]
    y = df["_value"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        line=dict(color="blue", width=2),
        marker=dict(size=4)
    ))

    fig.update_layout(
        title="Anomaly Timeline",
        template="plotly_white"
    )

    fig.update_xaxes(title="Time")
    fig.update_yaxes(title="Score")

    return fig
