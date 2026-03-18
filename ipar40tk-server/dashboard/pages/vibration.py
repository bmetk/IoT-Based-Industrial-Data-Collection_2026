import dash
from dash import dcc
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from components.health_indicator import health_indicator
from influx_query import *
import plotly.graph_objects as go

dash.register_page(__name__, path="/vibration")

layout = dbc.Container([

    dbc.Row([
        dbc.Col(dcc.Graph(id="rms-graph")),
        dbc.Col(dcc.Graph(id="fft-graph")),
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id="psd-graph"))
    ])

])

@dash.callback(

    Output("rms-graph","figure"),
    Output("fft-graph","figure"),
    Output("psd-graph","figure"),

    Input("machine-selector","value"),
    Input("vibration-tabs","value"),
    Input("refresh","n_intervals")

)
def update_vibration(machine, axis, _):

    df = query_vibration(machine, axis)
    if df is None or df.empty or "_value" not in df.columns:
        return go.Figure(), "No data"

    score = query_latest_anomaly(machine, "vibration")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["_time"],
            y=df["_value"],
            mode="lines"
        )
    )

    fig.update_layout(
        title=f"Vibration {axis}",
        template="plotly_dark"
    )

    if score is not None and score < -0.3:
        fig.update_layout(
            paper_bgcolor="rgba(255,0,0,0.15)"
        )

    return fig, health_indicator(score)