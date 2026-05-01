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
    dcc.Store(id="sim-config-store", storage_type="session"),

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