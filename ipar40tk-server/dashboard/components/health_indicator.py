from dash import html
import dash_bootstrap_components as dbc

def health_indicator(score, mean=None, std=None):

    if score is None:
        return dbc.Badge("UNKNOWN", color="secondary")

    if mean is None or std is None:
        return dbc.Badge("NO BASELINE", color="secondary")

    warning = mean - 2 * std
    anomaly = mean - 3 * std

    if score >= warning:
        return dbc.Badge("HEALTHY", color="success")

    elif score >= anomaly:
        return dbc.Badge("WARNING", color="warning")

    else:
        return dbc.Badge("ANOMALY", color="danger")