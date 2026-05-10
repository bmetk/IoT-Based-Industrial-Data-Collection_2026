import dash
from dash import dcc, html, Input, Output, no_update, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from influx_query import *
from dash.dcc import send_bytes
import pandas as pd
import io

dash.register_page(__name__, path="/")

layout = dbc.Container([

    dbc.Row([

        dbc.Col([
            dcc.Graph(id="rpm-gauge", style={"height": "300px"})
        ], width=4),

        dbc.Col([
            dcc.Graph(id="temp-gauge", style={"height": "300px"})
        ], width=4),

        dbc.Col([
            dcc.Graph(id="current-gauge", style={"height": "300px"})
        ], width=4),

    ], className="g-2"),

    html.Br(),

    dbc.Row([

        dbc.Col([

            dcc.Tabs(
                id="vibration-tabs",
                value="vibX",
                children=[
                    dcc.Tab(label="X axis", value="vibX"),
                    dcc.Tab(label="Y axis", value="vibY"),
                    dcc.Tab(label="Z axis", value="vibZ")
                ]
            ),
            dcc.Graph(id="vibration-graph")
        ])

    ]),

    html.Br(),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Export features data: Current-Mean, Current-Imbalance, RPM, Temperature, Vibraton RMS and FFT peaks by axis"),

                dbc.CardBody([

                    html.Label("Days back"),

                    dcc.Slider(
                        id="export-days",
                        min=1,
                        max=30,
                        step=1,
                        value=7,
                        marks={i: str(i) for i in [1,3,7,14,30]}
                    ),

                    html.Br(),

                    dbc.Button(
                        "Download XLSX",
                        id="download-home-xlsx-btn",
                        color="primary"
                    ),

                    dcc.Download(id="download-home-xlsx")
                ])
            ])
        ], width=12)
    ])
])


@dash.callback(
    Output("rpm-gauge","figure"),
    Output("temp-gauge","figure"),
    Output("current-gauge","figure"),

    Input("machine-selector","value"),
    Input("refresh","n_intervals")
)
def update_scalars(machine,_):

    df=query_features(machine)

    if df.empty:
        return no_update, no_update, no_update

    def get_latest(df, field):

        if df is None or df.empty:
            return None

        if "_field" not in df.columns or "_value" not in df.columns:
            return None

        sub = df[df["_field"] == field]

        if sub.empty:
            return None

        return float(sub["_value"].iloc[-1])
    
    def get_3phase(df):
        return (
            get_latest(df, "current_a"),
            get_latest(df, "current_b"),
            get_latest(df, "current_c"),
        )
    rpm = get_latest(df, "rpm")
    temp = get_latest(df, "tempC")
    

    rpm_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = rpm if rpm is not None else 0,
        title ={"text": "RPM (no data)" if rpm is None else "RPM", "font": {"size": 16}},
        gauge={"axis":{"range":[0,3000]},"bar": {"thickness": 0.3}},
        number={"font": {"size": 30}}
    ))

    temp_fig=go.Figure(go.Indicator(
        mode="gauge+number",
        value = temp if temp is not None else 0,
        title = {"text": "Temperature (no data)" if temp is None else "Temperature", "font": {"size": 16}},
        gauge={"axis":{"range":[0,120]},"bar": {"thickness": 0.3}},
        number={"font": {"size": 30}}
    ))

    ia, ib, ic = get_3phase(df)
    if all(v is None for v in [ia, ib, ic]):
        return (
            rpm_fig,
            temp_fig,
            go.Figure(),
        )

    values = [
        ia if ia is not None else 0,
        ib if ib is not None else 0,
        ic if ic is not None else 0
    ]

    current_fig = go.Figure(
        data=[
            go.Bar(
                x=["Phase A", "Phase B", "Phase C"],
                y=values,
                marker_color=["blue", "green", "orange"]
            )
        ]
    )

    current_fig.update_layout(
        title="Current (3-phase)",
        yaxis_title="Ampere",
    )

    return (
        rpm_fig,
        temp_fig,
        current_fig,
    )

@dash.callback(
    Output("vibration-graph", "figure"),
    Input("machine-selector", "value"),
    Input("vibration-tabs", "value"),
    Input("refresh", "n_intervals")
)
def update_vibration(machine, axis, _):

    df = query_fft(machine, axis)

    if df is None or df.empty:
        return go.Figure()

    x = df["freq"].astype(float)
    y = df["_value"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=x,
        y=y,
        marker_color="darkblue"
    ))

    fig.update_layout(
        title=f"Vibration spectrum ({axis})",
        template="plotly_white"
    )

    fig.update_xaxes(title="Frequency [Hz]")
    fig.update_yaxes(title="Amplitude", type="log")

    return fig

@dash.callback(
    Output("download-home-xlsx", "data"),
    Input("download-home-xlsx-btn", "n_clicks"),
    State("machine-selector", "value"),
    State("export-days", "value"),
    prevent_initial_call=True
)
def download_home_export(n_clicks, machine, days):

    df = query_home_export_data(machine, days)

    if df is None or df.empty:
        return None

    drop_cols = [
        "result",
        "table",
        "_start",
        "_stop"
    ]

    for col in drop_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    df["_time"] = df["_time"].dt.tz_localize(None)

    df = df.sort_values("_time")

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="features")

    output.seek(0)

    filename = f"{machine}_{days}d_export.xlsx"

    return send_bytes(output.getvalue(), filename)