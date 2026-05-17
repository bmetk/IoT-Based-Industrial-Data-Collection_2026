from dash import dcc

machine_selector = dcc.Dropdown(

    id="machine-selector",

    placeholder=" Search",

    options=[
        {"label": "TK Lathe", "value": "lathe00"},
        {"label": "Lathe 01", "value": "lathe01"},
        {"label": "Lathe 02", "value": "lathe02"},
        {"label": "Lathe 03", "value": "lathe03"},
        {"label": "Test Lathe 01", "value": "test-lathe01"},
        {"label": "Test Lathe 02", "value": "test-lathe02"},
    ],

    value="lathe01",

    persistence=True,
    persistence_type="local",

    style={"width":"500px", "display": "flex"}
)