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
            dcc.Graph(id="rpm-gauge", style={"height": "300px"})
        ], width=4),

        dbc.Col([
            dcc.Graph(id="temp-gauge", style={"height": "300px"})
        ], width=4),

        dbc.Col([
            dcc.Graph(id="current-gauge", style={"height": "300px"})
        ], width=4),

    ], className="g-2"),

    html.Br(),
    dbc.Row([

        dbc.Col([
            html.Div(id="status-table")
        ], width=12)

    ], className="g-2"),
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

], style={"padding": 0}, fluid=True )


@dash.callback(
    Output("rpm-gauge","figure"),

    Output("temp-gauge","figure"),

    Output("current-gauge","figure"),

    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_scalars(machine,_):

    df=query_features(machine)

    if df.empty:
        return no_update, no_update, no_update

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
    

    rpm_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = rpm if rpm is not None else 0,
        title ={"text": "RPM (no data)" if rpm is None else "RPM", "font": {"size": 16}},
        gauge={"axis":{"range":[0,3000]},"bar": {"thickness": 0.3}},
        number={"font": {"size": 30}}
    ))

    temp_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = temp if temp is not None else 0,
        title = {"text": "Temperature (no data)" if temp is None else "Temperature", "font": {"size": 16}},
        gauge={"axis":{"range":[0,120]},"bar": {"thickness": 0.3}},
        number={"font": {"size": 30}}
    ))

    ia, ib, ic = get_3phase(df)
    if all(v is None for v in [ia, ib, ic]):
        return (
            rpm_fig,
            temp_fig,
            go.Figure(),
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

        temp_fig,

        current_fig,
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

@dash.callback(
    Output("status-table", "children"),
    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_status(machine, _):

    df = query_status(machine)

    if df is None:
        return "No status data"

    def get(field, measurement):
        sub = df[(df["_field"] == field) & (df["_measurement"] == measurement)]
        if sub.empty:
            return None
        return sub.sort_values("_time").iloc[-1]["_value"]

    lathe_status_esp1_esp1 = get("esp1", "lathe_status_esp1")
    mqtt_esp1 = get("mqtt", "lathe_status_esp1")
    temp = get("temp", "lathe_status_esp1")
    rpm = get("rpm", "lathe_status_esp1")
    current = get("current", "lathe_status_esp1")
    lathe_status_esp1_esp2 = get("esp2", "lathe_status_esp1")
    esp2_collect = get("esp2_collect", "lathe_status_esp1")
    esp2_mpu = get("esp2_mpu", "lathe_status_esp1")
    
    lathe_status_esp2_esp2 = get("esp2", "lathe_status_esp2")
    mqtt_esp2 = get("mqtt", "lathe_status_esp2")
    mpu = get("mpu", "lathe_status_esp2")
    lathe_status_esp2_esp1 = get("esp1", "lathe_status_esp2")

    def badge(label, value):

        if value is True:
            color = "success"
            text = "OK"

        elif value is False:
            color = "danger"
            text = "OFF"

        elif value is None:
            color = "secondary"
            text = "N/A"

        else:
            color = "warning"
            text = str(value)

        return dbc.Badge(
            f"{label}: {text}",
            color=color,
            className="me-2",
            pill=True
        )

    return dbc.Card(
        dbc.CardBody([

            html.Div([
                badge("ESP1 self status", lathe_status_esp1_esp1),
                badge("ESP1 MQTT", mqtt_esp1),
                badge("TEMP", temp),
                badge("RPM", rpm),
                badge("CURRENT", current),
                badge("ESP2 status from ESP1", lathe_status_esp1_esp2),
                badge("ESP2 collection from ESP1", esp2_collect),
                badge("ESP2 mpu from ESP1", esp2_mpu),
                badge("ESP2 self status", lathe_status_esp2_esp2),
                badge("ESP2 MQTT", mqtt_esp2),
                badge("MPU", mpu),
                badge("ESP1 status from ESP2", lathe_status_esp2_esp1)
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "5px"})

        ], style={"padding": "5px"}),

        style={"marginTop": "5px"}
    )