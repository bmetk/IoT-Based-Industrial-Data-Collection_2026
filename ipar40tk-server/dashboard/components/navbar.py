import dash_bootstrap_components as dbc
from dash import html
from components.machine_selector import machine_selector

navbar = dbc.Navbar(

    dbc.Container([

        dbc.NavbarBrand("OpenMAPS Dashboard"),

        dbc.Nav([

            dbc.NavLink("Home", href="/"),
            dbc.NavLink("Vibration Analytics", href="/vibration"),
            dbc.NavLink("Anomalies", href="/anomalies"),
            dbc.NavLink("About", href="/about"),

        ], navbar=True),

        machine_selector
    ]),

    color="primary",
    dark=True
)