import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from influx_query import *
from components.health_indicator import health_indicator

dash.register_page(__name__, path="/experimental")

layout = dbc.Container([

    dbc.Row([

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Machine Health"),
                dbc.CardBody(html.H4(id="exp-state"))
                ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Operating State"),
                dbc.CardBody(html.H3(id="exp-health"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("RUL"),
                dbc.CardBody(html.H3(id="exp-rul"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Anomaly Severity"),
                dbc.CardBody(html.H3(id="exp-severity"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Anomaly"),
                dbc.CardBody(html.H3(id="exp-anomaly"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Is Anomaly?"),
                dbc.CardBody(html.H3(id="exp-is-anomaly"))
            ])
        ], width=3)

    ], className="g-2"),

    html.Br(),

    dbc.Row([

        dbc.Col([
            html.Div(id="exp-status-table")
        ], width=12)

    ])

], fluid=True)


# =========================================================
# VIBRATION + ML DATA
# =========================================================

@dash.callback(
    Output("exp-health", "children"),
    Output("exp-rul", "children"),
    Output("exp-severity", "children"),
    Output("exp-anomaly", "children"),
    Output("exp-is-anomaly", "children"),
    Output("exp-state", "children"),

    Input("machine-selector", "value"),
    Input("refresh", "n_intervals")
)
def update_experimental(machine, _):


    # =========================
    # ML RESULTS
    # =========================

    prediction = query_features(machine)

    if prediction is None or prediction.empty:

        return (
            "No ML data",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A"
        )

    def get_latest(field):

        sub = prediction[prediction["_field"] == field]

        if sub.empty:
            return None

        return sub.sort_values("_time").iloc[-1]["_value"]

    health = get_latest("health")
    rul = get_latest("rul")
    severity = get_latest("anomaly_severity")
    is_anomaly = get_latest("is_anomaly")
    state = get_latest("state")
    score = query_latest_anomaly(machine, "combined")

    state_text = state if state is not None else "N/A"

    # HEALTH UI
    health_text = float(health) if health is not None else "N/A"

    # RUL
    if rul is not None:
        rul_text = f"{float(rul):.1f} h"
    else:
        rul_text = "N/A"

    # SEVERITY
    if severity is not None:
        severity_text = f"{float(severity):.4f}"
    else:
        severity_text = "0"

    # ANOMALY
    if is_anomaly == 1:
        anomaly_text = "YES"
    else:
        anomaly_text = "NO"

    prediction = health_indicator(score)

    return (
        state_text,
        health_text,
        rul_text,
        severity_text,
        anomaly_text,
        prediction
    )


# =========================================================
# STATUS TABLE
# =========================================================

@dash.callback(
    Output("exp-status-table", "children"),
    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_status(machine, _):

    df = query_status(machine)

    if df is None:
        return "No status data"

    def get(field, measurement):

        sub = df[
            (df["_field"] == field) &
            (df["_measurement"] == measurement)
        ]

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

            ], style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "5px"
            })

        ], style={"padding": "5px"}),

        style={"marginTop": "5px"}
    )