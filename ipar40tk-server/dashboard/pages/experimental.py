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
                dbc.CardBody(html.Div(id="exp-health"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Operating State"),
                dbc.CardBody(html.H4(id="exp-state"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Classifier Confidence"),
                dbc.CardBody(html.H3(id="exp-confidence"))
            ])
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("RUL"),
                dbc.CardBody(html.H3(id="exp-rul"))
            ])
        ], width=3),

    ], className="g-2"),

    html.Br(),

    dbc.Row([

        dbc.Col([
            dcc.Graph(
                id="state-probabilities-chart"
            )
        ], width=8),

        dbc.Col([
            dcc.Graph(
                id="confidence-gauge"
            )
        ], width=4),

    ]),

    html.Br(),

    dbc.Row([

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Diagnostic Summary"),
                dbc.CardBody(
                    html.Div(id="diagnostic-summary")
                )
            ])
        ])

    ]),

    html.Br(),

    dbc.Row([
        dbc.Col([
            html.Div(id="exp-status-table")
        ])
    ])
    

], fluid=True)


# =========================================================
# VIBRATION + ML DATA
# =========================================================

@dash.callback(
    Output("exp-health", "children"),
    Output("exp-rul", "children"),
    Output("exp-state", "children"),
    Output("exp-confidence", "children"),

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
            "N/A"
        )

    def get_latest(field):

        sub = prediction[prediction["_field"] == field]

        if sub.empty:
            return None

        return sub.sort_values("_time").iloc[-1]["_value"]

    rul = get_latest("rul")
    state = get_latest("state")
    score = query_latest_anomaly(machine, "combined")
    confidence = get_latest("classifier_confidence")

    state_text = state if state is not None else "N/A"

    # RUL
    if rul is not None:
        rul_text = f"{float(rul):.1f} h"
    else:
        rul_text = "N/A"

    confidence_text = (f"{float(confidence)*100:.1f}%" if confidence is not None else "N/A")

    prediction = health_indicator(score)

    return (
        prediction,
        rul_text,
        state_text,
        confidence_text
    )

@dash.callback(
    Output("state-probabilities-chart", "figure"),
    Input("machine-selector", "value"),
    Input("refresh", "n_intervals")
)
def update_state_probabilities(machine, _):

    prediction = query_features(machine)

    classifier_rows = prediction[
        prediction["_field"].str.startswith(
            "classifier_"
        )
    ]

    probs = {}

    for field in classifier_rows["_field"].unique():

        if field in [
            "classifier_confidence",
            "classifier_predicted_state"
        ]:
            continue

        sub = classifier_rows[
            classifier_rows["_field"] == field
        ]

        if sub.empty:
            continue

        value = (
            sub.sort_values("_time")
            .iloc[-1]["_value"]
        )

        state = field.replace(
            "classifier_",
            ""
        )

        probs[state] = float(value)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=list(probs.values()),
            y=list(probs.keys()),
            orientation="h"
        )
    )

    fig.update_layout(
        title="State Probabilities",
        height=450,
        margin=dict(
            l=20,
            r=20,
            t=40,
            b=20
        )
    )

    return fig

@dash.callback(
    Output("confidence-gauge", "figure"),
    Input("machine-selector", "value"),
    Input("refresh", "n_intervals")
)
def update_confidence(machine, _):

    prediction = query_features(machine)

    def get_latest(field):

        sub = prediction[prediction["_field"] == field]

        if sub.empty:
            return None

        return sub.sort_values("_time").iloc[-1]["_value"]

    confidence = float(get_latest("classifier_confidence") or 0)

    confidence *= 100

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence,
            title={"text":"Classifier"},
            gauge={
                "axis":{
                    "range":[0,100]
                },
                "steps":[
                    {"range":[0,50]},
                    {"range":[50,80]},
                    {"range":[80,100]}
                ]
            }
        )
    )

    return fig

@dash.callback(
    Output("diagnostic-summary", "children"),
    Input("machine-selector", "value"),
    Input("refresh", "n_intervals")
)
def update_diagnostic_summary(machine, _):

    prediction = query_features(machine)

    def get_latest(field):

        sub = prediction[prediction["_field"] == field]

        if sub.empty:
            return None

        return sub.sort_values("_time").iloc[-1]["_value"]

    state = get_latest("classifier_predicted_state")
    confidence = get_latest("classifier_confidence")
    health = get_latest("health")
    rul = get_latest("rul")
    severity = get_latest("anomaly_severity")

    confidence_text = (f"{float(confidence)*100:.1f}%" if confidence is not None else "N/A")

    health_text = (f"{float(health):.1f}" if health is not None else "N/A")

    rul_text = (f"{float(rul):.1f} h" if rul is not None else "N/A")

    severity_text = (f"{float(severity):.4f}" if severity is not None else "N/A")

    return html.Div([

        html.H5("Diagnostic Summary"),

        html.Ul([
            html.Li(f"Predicted State: {state or 'N/A'}"),
            html.Li(f"Confidence: {confidence_text}"),
            html.Li(f"Health: {health_text}"),
            html.Li(f"RUL: {rul_text}"),
            html.Li(f"Severity: {severity_text}")
        ])
    ])

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