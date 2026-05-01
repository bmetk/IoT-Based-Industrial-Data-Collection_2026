import dash
from dash import html, dcc, Input, Output, State, callback, no_update
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
        ], width=4),
    ], className="mb-3"),

    html.Hr(),
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
                ],
                value=None
            ),

            html.Br(),

            html.Label("Fault intensity"),
            dcc.Slider(id="fault-intensity", min=0, max=1, step=0.05, value=0)
        ]),
        dbc.Col([
            dbc.Button("Apply config", id="apply-config", color="success")
        ], width=2, style={"marginTop": "20px"})
    ]),
    
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
    Output("config-preview", "children"),
    Output("sim-config-store", "data"),
    Input("rpm-mode", "value"),
    Input("load-mode", "value"),
    Input("wear-slider", "value"),
    Input("wear-rate", "value"),
    Input("fault-mode", "value"),
    Input("fault-intensity", "value"),
)
def build_config(rpm, load, wear, wear_rate, fault, intensity):

    config = {
        "rpm_mode": rpm,
        "load": load,
        "wear": wear,
        "wear_rate": wear_rate,
        "fault": fault,
        "fault_intensity": intensity
    }

    return json.dumps(config, indent=2), config

@callback(
    Input("apply-config", "n_clicks"),
    State("machine-store", "data"),
    State("sim-config-store", "data"),
    prevent_initial_call=True
)
def apply_config(_, machine, config):

    if not machine or not config:
        return no_update

    requests.post(
        f"http://simulator:9000/config/{machine}",
        params=config
    )

    return no_update

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
        "fault": "bearing"
    },
    "stress": {
        "rpm_mode": "high",
        "load": "high",
        "wear": 0.2,
        "fault": "misalignment"
    }
}

@callback(
    Output("rpm-mode", "value"),
    Output("load-mode", "value"),
    Output("wear-slider", "value"),
    Output("wear-rate", "value"),
    Output("fault-mode", "value"),
    Output("fault-intensity", "value"),
    Input("apply-preset", "n_clicks"),
    State("preset-selector", "value"),
    prevent_initial_call=True
)
def apply_preset(_, preset):

    p = PRESETS.get(preset, {})

    return (
        p.get("rpm_mode", "low"),
        p.get("load", "idle"),
        p.get("wear", 0),
        p.get("wear_rate", 0.002),
        p.get("fault", None),
        p.get("fault_intensity", 0),
    )