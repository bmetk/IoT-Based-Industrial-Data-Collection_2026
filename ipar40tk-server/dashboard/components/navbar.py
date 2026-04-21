import dash_bootstrap_components as dbc
from dash import html, ctx, no_update
import requests
from dash import Input, Output, callback, dcc
from components.machine_selector import machine_selector

navbar = dbc.Navbar(

    dbc.Container([

        html.Div([
            html.Img(
                src="/assets/VIKTK.svg",
                height="50px",
                style={"borderRadius": "20%", "marginRight": "10px", "background-color": "white"}
            ),
            dbc.NavbarBrand("OpenMAPS Dashboard"),
        ], style={"display": "flex", "alignItems": "left"}),

        dbc.Nav([

            dbc.NavLink("Home", href="/"),
            dbc.NavLink("Vibration Analytics", href="/vibration"),
            dbc.NavLink("Anomalies", href="/anomalies"),
            dbc.NavLink("About", href="/about"),

        ], navbar=True),

        html.Div([
            machine_selector,

            dbc.Switch(
                id="sim-toggle",
                label="Simulation",
                value=False,
                style={"marginLeft": "20px", "color": "white"}
            ),
            dbc.Select( 
                id="rpm-mode", 
                options=[ {"label": "Low RPM", "value": "low"},
                          {"label": "Medium RPM", "value": "medium"},
                          {"label": "High RPM", "value": "high"},
                        ], 
                value="low",
                style={"width": "150px"} 
            ),
            dcc.Slider(
                id="wear-slider",
                min=0,
                max=1,
                step=0.05,
                value=0,
                marks={0: "0", 0.5: "0.5", 1: "1"},
                tooltip={"placement": "bottom"}
            )
        ], style={"display": "flex", "alignItems": "center", "gap": "10px"})

    ], style={"display": "flex", "padding": 0}, fluid=True),

    color="primary",
    dark=True
)

API_URL = "http://simulator:9000"

@callback(
    Output("sim-toggle", "label"),
    Input("sim-toggle", "value"),
    Input("machine-selector", "value"),
    Input("rpm-mode", "value"),
    Input("wear-slider", "value"),
    prevent_initial_call=False
)
def control_simulation(toggle, machine, rpm_mode, wear):

    trigger = ctx.triggered_id

    if not machine or not machine.startswith("test-"):
        return "Simulation (disabled)"

    try:
        if trigger == "machine-selector" or trigger is None:
            res = requests.get(f"{API_URL}/status/{machine}", timeout=2)
            running = res.json().get("running", False)

            if running:
                return "Simulation ON", True
            else:
                return "Simulation OFF", False

        if trigger == "sim-toggle":
            if toggle:
                requests.post(
                    f"{API_URL}/start/{machine}",
                    params={"rpm_mode": rpm_mode, "wear": wear},
                    timeout=2
                )
                return "Simulation ON", True
            else:
                requests.post(f"{API_URL}/stop/{machine}", timeout=2)
                return "Simulation OFF", False

        if trigger in ["rpm-mode", "wear-slider"]:
            requests.post(
                f"{API_URL}/config/{machine}",
                params={"rpm_mode": rpm_mode, "wear": wear},
                timeout=2
            )
            return no_update

    except Exception as e:
        print(e)
        return "ERROR", False

    return no_update