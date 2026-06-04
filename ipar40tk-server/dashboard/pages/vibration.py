# This page provides visualizations of vibration features such as RMS, FFT peaks and PSD peaks for the monitored machines and also includes an export feature for downloading data in XLSX format.

import dash
from dash import dcc, html, Input, Output, no_update, State
import dash_bootstrap_components as dbc
from influx_query import *
import plotly.graph_objects as go
from dash.dcc import send_bytes
import pandas as pd
import io

dash.register_page(__name__, path="/vibration")

layout = dbc.Container([

    dbc.Row([

        dbc.Col([
            dcc.Tabs(
                id="vibration-rms-tabs",
                value="vibX_rms",
                children=[
                    dcc.Tab(label="X axis", value="vibX_rms"),
                    dcc.Tab(label="Y axis", value="vibY_rms"),
                    dcc.Tab(label="Z axis", value="vibZ_rms")
                ]
            ),
            dcc.Graph(id="rms-graph")
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Tabs(
                id="vibration-fftpeak-tabs",
                value="vibX_fft_peak",
                children=[
                    dcc.Tab(label="X axis", value="vibX_fft_peak"),
                    dcc.Tab(label="Y axis", value="vibY_fft_peak"),
                    dcc.Tab(label="Z axis", value="vibZ_fft_peak")
                ]
            ),
            dcc.Graph(id="fft-peak-graph")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Tabs(
                id="vibration-psd-tabs",
                value="vibX_psd_peak",
                children=[
                    dcc.Tab(label="X axis", value="vibX_psd_peak"),
                    dcc.Tab(label="Y axis", value="vibY_psd_peak"),
                    dcc.Tab(label="Z axis", value="vibZ_psd_peak")
                ]
            ),
            dcc.Graph(id="psd-graph")
        ])
    ]),
    html.Br(),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Export features data: Vibraton RMS, FFT peaks and PSD peaks by axis"),

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
                        id="download-vibration-xlsx-btn",
                        color="primary"
                    ),

                    dcc.Download(id="download-vibration-xlsx")
                ])
            ])
        ], width=12)
    ])
])

@dash.callback(
    Output("rms-graph","figure"),
    Output("fft-peak-graph","figure"),
    Output("psd-graph","figure"),

    Input("machine-selector","value"),
    Input("vibration-rms-tabs","value"),
    Input("vibration-fftpeak-tabs","value"),
    Input("vibration-psd-tabs","value"),
    Input("refresh","n_intervals")
)
def update_vibration(machine, rms_axis, fftpeak_axis, psd_axis, _):

    df_rms = query_vibration(machine, rms_axis)
    df_fftpeak = query_vibration(machine, fftpeak_axis)
    df_psd = query_vibration(machine, psd_axis)

    fig_rms = go.Figure()
    fig_fftpeak = go.Figure()
    fig_psd = go.Figure()

    # RMS
    if df_rms is not None and not df_rms.empty:
        df_rms = df_rms.sort_values("_time")

        fig_rms.add_trace(go.Scatter(
            x=df_rms["_time"],
            y=df_rms["_value"],
            mode="lines",
            line=dict(color="blue")
        ))

        fig_rms.update_layout(
            title=f"Vibration RMS {rms_axis}",
            template="plotly_white"
        )

        fig_rms.update_xaxes(title="Time")
        fig_rms.update_yaxes(title="Amplitude")

    # FFT Peak
    if df_fftpeak is not None and not df_fftpeak.empty:
        df_fftpeak = df_fftpeak.sort_values("_time")

        fig_fftpeak.add_trace(go.Scatter(
            x=df_fftpeak["_time"],
            y=df_fftpeak["_value"],
            mode="lines",
            line=dict(color="orange")
        ))

        fig_fftpeak.update_layout(
            title=f"FFT Peak {fftpeak_axis}",
            template="plotly_white"
        )

        fig_fftpeak.update_xaxes(title="Time")
        fig_fftpeak.update_yaxes(title="Amplitude")

    # PSD Peak
    if df_psd is not None and not df_psd.empty:
        df_psd = df_psd.sort_values("_time")

        fig_psd.add_trace(go.Scatter(
            x=df_psd["_time"],
            y=df_psd["_value"],
            mode="lines",
            line=dict(color="green")
        ))

        fig_psd.update_layout(
            title=f"PSD Peak {psd_axis}",
            template="plotly_white"
        )

        fig_psd.update_xaxes(title="Time")
        fig_psd.update_yaxes(title="Amplitude")

    return fig_rms, fig_fftpeak, fig_psd

@dash.callback(
    Output("download-vibration-xlsx", "data"),
    Input("download-vibration-xlsx-btn", "n_clicks"),
    State("machine-selector", "value"),
    State("export-days", "value"),
    prevent_initial_call=True
)
def download_vibration_export(n_clicks, machine, days):

    df = query_vibration_export_data(machine, days)

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

    filename = f"{machine}_{days}d__vibration_export.xlsx"

    return send_bytes(output.getvalue(), filename)