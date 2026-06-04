# Main application file for the IPAR40TK server dashboard
# This file initializes the Dash app, sets up the layout and routing for different pages, and starts the server to serve the dashboard on port 8050.
# The dashboard provides interactive visualizations and controls for monitoring machine condition, analyzing telemetry data, and managing the simulation environment. 
# It integrates with the backend services to fetch real-time data and display it in an intuitive format for users.

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from components.navbar import navbar

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY]
)

app.layout = dbc.Container([

    dcc.Store(id="machine-store", storage_type="local"),
    dcc.Store(id="sim-config-store", storage_type="local"),

    dcc.Interval(
        id="refresh",
        interval=4000,
        n_intervals=0
    ),

    navbar,

    dash.page_container

], style={"padding":0}, fluid=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)