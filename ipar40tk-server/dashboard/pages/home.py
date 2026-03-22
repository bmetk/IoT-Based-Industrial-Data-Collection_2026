import dash
from dash import dcc, html, Input, Output
from dash import no_update
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

    if df.empty:
        return no_update, no_update, no_update, no_update, no_update, no_update

    def get_latest(df, field):

        if df is None or df.empty:
            return None

        if "_field" not in df.columns or "_value" not in df.columns:
            return None

        sub = df[df["_field"] == field]

        if sub.empty:
            return None

        return float(sub["_value"].iloc[-1])
    
    def get_3phase(df):
        return (
            get_latest(df, "current_a"),
            get_latest(df, "current_b"),
            get_latest(df, "current_c"),
        )
    rpm = get_latest(df, "rpm")
    temp = get_latest(df, "tempC")
    
    rpm_score = query_latest_anomaly(machine, "combined")
    rpm_mean, rpm_std = query_anomaly_stats(machine, "combined")

    temp_score = query_latest_anomaly(machine, "combined")
    temp_mean, temp_std = query_anomaly_stats(machine, "combined")

    current_score = query_latest_anomaly(machine, "combined")
    current_mean, current_std = query_anomaly_stats(machine, "combined")

    rpm_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = rpm if rpm is not None else 0,
        title = "RPM (no data)" if rpm is None else "RPM",
        gauge={"axis":{"range":[0,3000]}}
    ))

    temp_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = temp if temp is not None else 0,
        title = "Temperature (no data)" if temp is None else "Temperature",
        gauge={"axis":{"range":[0,120]}}
    ))

    ia, ib, ic = get_3phase(df)
    if all(v is None for v in [ia, ib, ic]):
        return (
            rpm_fig, "No data",
            temp_fig, "No data",
            go.Figure(), "No data"
        )

    values = [
        ia if ia is not None else 0,
        ib if ib is not None else 0,
        ic if ic is not None else 0
    ]

    current_fig = go.Figure(
        data=[
            go.Bar(
                x=["Phase A", "Phase B", "Phase C"],
                y=values,
                marker_color=["blue", "green", "orange"]
            )
        ]
    )

    current_fig.update_layout(
        title="Current (3-phase)",
        yaxis_title="Ampere",
    )

    return (
        rpm_fig,
        health_indicator(rpm_score),

        temp_fig,
        health_indicator(temp_score),

        current_fig,
        health_indicator(current_score)
    )

@dash.callback(
    Output("vibration-graph", "figure"),
    Output("vibration-health", "children"),
    Input("machine-selector", "value"),
    Input("vibration-tabs", "value"),
    Input("refresh", "n_intervals")
)
def update_vibration(machine, axis, _):

    df = query_fft(machine, axis)

    if df is None or df.empty:
        return go.Figure(), "No data"

    x = df["freq"].astype(float)
    y = df["_value"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=x,
        y=y,
        marker_color="darkblue"
    ))

    fig.update_layout(
        title=f"Vibration spectrum ({axis})",
        template="plotly_white"
    )

    fig.update_xaxes(title="Frequency [Hz]")
    fig.update_yaxes(title="Amplitude", type="log")

    # anomaly
    score = query_latest_anomaly(machine, "combined")
    mean, std = query_anomaly_stats(machine, "combined")

    health = health_indicator(score)

    return fig, health