import dash_bootstrap_components as dbc
from dash import html
import requests
from dash import Input, Output, callback, dcc
from components.machine_selector import machine_selector

navbar = dbc.Navbar(

    dbc.Container([

        html.Div([
            html.Img(
                src="/assets/logo.png",
                height="40px",
                style={"borderRadius": "20%", "marginRight": "10px"}
            ),
            dbc.NavbarBrand("OpenMAPS Dashboard"),
        ], style={"display": "flex", "alignItems": "center"}),

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

    ]),

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
    prevent_initial_call=True
)
def control_simulation(toggle, machine, rpm_mode, wear):

    if not machine or not machine.startswith("test-"):
        return "Simulation (disabled)"

    try:
        if toggle:
            requests.post(f"{API_URL}/start/{machine}")

            # Send config parameters to the simulator
            requests.post(
                f"{API_URL}/config/{machine}",
                params={
                    "rpm_mode": rpm_mode,
                    "wear": wear
                }
            )

            return "Simulation ON"

        else:
            requests.post(f"{API_URL}/stop/{machine}")
            return "Simulation OFF"

    except Exception as e:
        print(e)
        return "ERROR"