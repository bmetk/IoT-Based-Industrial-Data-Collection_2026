import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import json
import requests

dash.register_page(__name__, path="/simulation")

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Simulation Control Center")
        ], width=8),

        dbc.Col([
            dbc.Badge(id="sim-status-badge", color="secondary")
        ], width=2)
    ], className="mb-2"),

    dbc.Row([
        
        dbc.Col([
            dcc.Dropdown(
                id="preset-selector",
                options=[
                    {"label": "Normal operation", "value": "normal"},
                    {"label": "High wear test", "value": "wear"},
                    {"label": "Fault injection", "value": "fault"},
                    {"label": "Stress test", "value": "stress"},
                ],
                placeholder="Scenario preset"
            )
        ], width=4),

        dbc.Col([
            dbc.Button("Apply preset", id="apply-preset", color="primary")
        ], width=4)
    ], className="mb-3"),

    html.Hr(),
    dbc.Row([
       dbc.Col([
            dbc.Button("Apply config", id="apply-config", color="success")
        ], width="auto", style={"marginTop": "20px", "marginBottom": "10px"})
    ], justify="center", className="mb-3"),
    dcc.Tabs([
        dcc.Tab(label="Operation", children=[

            dbc.Row([
                dbc.Col([
                    html.Label("RPM mode"),
                    dcc.Dropdown(
                        id="rpm-mode",
                        options=[
                            {"label": "Low", "value": "low"},
                            {"label": "Medium", "value": "medium"},
                            {"label": "High", "value": "high"},
                        ],
                        value="low"
                    )
                ], width=4),

                dbc.Col([
                    html.Label("Load"),
                    dcc.Dropdown(
                        id="load-mode",
                        options=[
                            {"label": "Idle", "value": "idle"},
                            {"label": "Low stress", "value": "low"},
                            {"label": "High stress", "value": "high"},
                        ],
                        value="idle"
                    )
                ], width=4),

                dbc.Col([
                    html.Label("Temperature bias"),
                    dcc.Slider(
                        id="temp-bias",
                        min=0,
                        max=20,
                        step=1,
                        value=0
                    )
                ], width=4),
            ])

        ]),

        dcc.Tab(label="Wear model", children=[

            html.Label("Wear level"),
            dcc.Slider(id="wear-slider", min=0, max=1, step=0.01, value=0),

            html.Br(),

            html.Label("Wear rate"),
            dcc.Slider(id="wear-rate", min=0.0001, max=0.01, step=0.0001, value=0.002),
        ]),

        dcc.Tab(label="Fault injection", children=[

            dcc.Dropdown(
                id="fault-mode",
                options=[
                    {"label": "None", "value": None},
                    {"label": "Imbalance", "value": "imbalance"},
                    {"label": "Misalignment", "value": "misalignment"},
                    {"label": "Bearing fault", "value": "bearing"},
                    {"label": "Looseness", "value": "looseness"},
                ],placeholder="Fault type",
                value=None
            ),

            html.Br(),

            html.Label("Fault intensity"),
            dcc.Slider(id="fault-intensity", min=0, max=1, step=0.05, value=0)
        ])
    ]),
    html.Hr(),
    dbc.Card([
        dbc.CardHeader("Live config snapshot"),
        dbc.CardBody([
            html.Pre(id="config-preview", style={
                "backgroundColor": "#111",
                "color": "#0f0",
                "padding": "10px",
                "borderRadius": "5px"
            })
        ])
    ])
])

@callback(
    Output("rpm-mode", "value"),
    Output("load-mode", "value"),
    Output("wear-slider", "value"),
    Output("wear-rate", "value"),
    Output("fault-mode", "value"),
    Output("fault-intensity", "value"),
    Output("config-preview", "children"),
    Input("sim-config-store", "data"),
)
def load_from_store(config):

    if not config:
        config = {
            "rpm_mode": "low",
            "load": "idle",
            "wear": 0,
            "wear_rate": 0.002,
            "fault": None,
            "fault_intensity": 0
        }

    return (
        config.get("rpm_mode", "low"),
        config.get("load", "idle"),
        config.get("wear", 0),
        config.get("wear_rate", 0.002),
        config.get("fault", None),
        config.get("fault_intensity", 0),
        json.dumps({
            "rpm_mode": config.get("rpm_mode", "low"),
            "load": config.get("load", "idle"),
            "wear": config.get("wear", 0),
            "wear_rate": config.get("wear_rate", 0.002),
            "fault": config.get("fault", None),
            "fault_intensity": config.get("fault_intensity", 0),
        }, indent=2)
    )


@callback(
    Input("sim-config-store", "data"),
    State("machine-store", "data"),
    prevent_initial_call=True
)
def push_to_api(config, machine):

    if not machine or not config:
        return
    if ctx.triggered_id != "apply-config":
        return
    requests.post(
        f"http://simulator:9000/config/{machine}",
        params=config
    )

DEFAULT_CONFIG = {
    "rpm_mode": "low",
    "load": "idle",
    "wear": 0,
    "wear_rate": 0.002,
    "fault": None,
    "fault_intensity": 0
}

PRESETS = {
    "normal": {
        "rpm_mode": "low",
        "load": "idle",
        "wear": 0.1,
        "fault": None
    },
    "wear": {
        "rpm_mode": "medium",
        "load": "low",
        "wear": 0.7,
        "wear_rate": 0.005
    },
    "fault": {
        "rpm_mode": "medium",
        "load": "high",
        "wear": 0.3,
        "fault": "bearing",
        "fault_intensity": 0.5

    },
    "stress": {
        "rpm_mode": "high",
        "load": "high",
        "wear": 0.2,
        "fault": "misalignment",
        "fault_intensity": 0.8
    }
}

@callback(
    Output("sim-config-store", "data"),
    Input("apply-preset", "n_clicks"),
    Input("apply-config", "n_clicks"),
    State("preset-selector", "value"),
    State("rpm-mode", "value"),
    State("load-mode", "value"),
    State("wear-slider", "value"),
    State("wear-rate", "value"),
    State("fault-mode", "value"),
    State("fault-intensity", "value"),
    prevent_initial_call=True
)
def update_store(preset_click, config_click, preset, rpm, load, wear, wear_rate, fault, intensity):

    trigger = ctx.triggered_id

    if trigger == "apply-preset":
        base = DEFAULT_CONFIG.copy()
        base.update(PRESETS.get(preset, {}))
        return base

    if trigger == "apply-config":
        return {
            "rpm_mode": rpm,
            "load": load,
            "wear": wear,
            "wear_rate": wear_rate,
            "fault": fault,
            "fault_intensity": intensity
        }

    raise dash.exceptions.PreventUpdate