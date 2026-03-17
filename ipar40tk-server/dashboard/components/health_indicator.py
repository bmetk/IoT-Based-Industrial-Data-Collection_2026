from dash import html
import dash_bootstrap_components as dbc

def health_indicator(score):

    if score is None:
        return dbc.Badge("UNKNOWN", color="secondary")

    if score > -0.1:
        return dbc.Badge("HEALTHY", color="success")

    elif score > -0.3:
        return dbc.Badge("WARNING", color="warning")

    else:
        return dbc.Badge("ANOMALY", color="danger")