import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from influx_query import *
from components.health_indicator import health_indicator

dash.register_page(__name__, path="/")

layout = dbc.Container([

    dbc.Row([

        dbc.Col([
            dcc.Graph(id="rpm-gauge"),
            html.Div(id="rpm-health")
        ]),

        dbc.Col([
            dcc.Graph(id="temp-gauge"),
            html.Div(id="temp-health")
        ]),

        dbc.Col([
            dcc.Graph(id="current-gauge"),
            html.Div(id="current-health")
        ]),

    ]),

    html.Br(),

    dbc.Row([

        dbc.Col([

            dcc.Tabs(
                id="vibration-tabs",
                value="vibX",
                children=[
                    dcc.Tab(label="X axis", value="vibX"),
                    dcc.Tab(label="Y axis", value="vibY"),
                    dcc.Tab(label="Z axis", value="vibZ")
                ]
            ),

            dcc.Graph(id="vibration-graph"),

            html.Div(id="vibration-health")

        ])

    ])

])


@dash.callback(
    Output("rpm-gauge","figure"),
    Output("rpm-health","children"),

    Output("temp-gauge","figure"),
    Output("temp-health","children"),

    Output("current-gauge","figure"),
    Output("current-health","children"),

    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_scalars(machine,_):

    df=query_features(machine)

    rpm=df[df["_field"]=="rpm"]["_value"].iloc[-1]
    temp=df[df["_field"]=="temperature"]["_value"].iloc[-1]
    current=df[df["_field"]=="current"]["_value"].iloc[-1]

    #rpm_score=query_latest_anomaly(machine,"rpm")
    #temp_score=query_latest_anomaly(machine,"temperature")
    #current_score=query_latest_anomaly(machine,"current")

    rpm_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value=rpm,
        title={"text":"RPM"},
        gauge={"axis":{"range":[0,3000]}}
    ))

    temp_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp,
        title={"text":"Temperature"},
        gauge={"axis":{"range":[0,120]}}
    ))

    current_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value=current,
        title={"text":"Current"},
        gauge={"axis":{"range":[0,20]}}
    ))

    return (
        rpm_fig,
        #health_indicator(rpm_score),

        temp_fig,
        #health_indicator(temp_score),

        current_fig,
        #health_indicator(current_score)
    )