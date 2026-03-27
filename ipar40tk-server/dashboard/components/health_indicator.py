from dash import html
import dash_bootstrap_components as dbc

def health_indicator(score):

    if score is None:
        return dbc.Badge("UNKNOWN", color="secondary")

    # Normalize score to 0-100% range
    min_s = -0.3
    max_s = 0.15

    score = max(min(score, max_s), min_s)
    health = (score - min_s) / (max_s - min_s)
    percent = int(health * 100)

    # Status thresholds
    if percent > 70:
        color = "success"
        label = "HEALTHY"
    elif percent > 40:
        color = "warning"
        label = "WARNING"
    else:
        color = "danger"
        label = "ANOMALY"

    return dbc.Container([

        dbc.Progress(
            value=percent,
            color=color,
            style={"height": "20px"}
        ),

        html.Div(
            f"{label} ({percent}%) | score: {round(score,3)}",
            style={"marginTop": "5px", "fontSize": "14px"}
        )
])