import dash
from dash import dcc
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import components.health_indicator as health_indicator
from influx_query import *

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

    Output("vibration-graph","figure"),
    Output("vibration-health","children"),

    Input("machine-selector","value"),
    Input("vibration-tabs","value"),
    Input("refresh","n_intervals")

)
def update_vibration(machine,axis,_):

    df=query_vibration(machine,axis)

    score=query_latest_anomaly(machine,"vibration")

    fig=go.Figure()

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

    if score < -0.3:
        fig.update_layout(
            paper_bgcolor="rgba(255,0,0,0.15)"
        )

    return fig,health_indicator(score)