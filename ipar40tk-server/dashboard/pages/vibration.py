import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from influx_query import *
import plotly.graph_objects as go

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