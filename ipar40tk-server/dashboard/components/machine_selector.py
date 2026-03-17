from dash import dcc

machine_selector = dcc.Dropdown(

    id="machine-selector",

    options=[
        {"label": "Lathe 01", "value": "lathe01"},
        {"label": "Lathe 02", "value": "lathe02"},
        {"label": "Lathe 03", "value": "lathe03"},
    ],

    value="lathe01",

    persistence=True,
    persistence_type="local",

    style={"width":"200px"}
)