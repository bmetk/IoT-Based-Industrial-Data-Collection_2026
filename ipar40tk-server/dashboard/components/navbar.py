# This module defines the navigation bar component for the OpenMAPS Dashboard.
# The navbar includes links to different pages and a toggle for simulation mode.

import dash_bootstrap_components as dbc
from dash import html, ctx, no_update, Input, Output, callback, dcc, State
import requests
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
            dbc.NavLink("Simulation", href="/simulation"),
            dbc.NavLink("Experimental Features", href="/experimental"),
            dbc.NavLink("About", href="/about"),

        ], navbar=True),

        html.Div([
            machine_selector,

            dbc.Switch(
                id="sim-toggle",
                label="Simulation",
                value=False,
                style={"marginLeft": "20px", "color": "white"}
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
    State("sim-config-store", "data"),
    prevent_initial_call=False
)
def control_simulation(toggle, machine, config):

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
                if not config:
                    return "No config", False
                requests.post(
                    f"{API_URL}/start/{machine}",
                    params=config,
                    timeout=2
                )
                return "Simulation ON", True
            else:
                requests.post(f"{API_URL}/stop/{machine}", timeout=2)
                return "Simulation OFF", False
    except Exception as e:
        print(e)
        return "ERROR", False

    return no_update