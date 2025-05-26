from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd

pressure_history = pd.DataFrame(columns=["ingame_minutes", "CORE_PRESSURE"])

def render_pressurizer_tab(data):
    global pressure_history

    core_pressure = data.get("CORE_PRESSURE", 0)
    core_pressure_max = data.get("CORE_PRESSURE_MAX", 200)
    core_pressure_oper = data.get("CORE_PRESSURE_OPERATIVE", 155)
    ingame_time = data.get("TIME_STAMP", 0)

    # --- History ---
    new_row = pd.DataFrame({"ingame_minutes": [ingame_time], "CORE_PRESSURE": [core_pressure]})
    pressure_history = pd.concat([pressure_history, new_row], ignore_index=True)
    pressure_history = pressure_history[pressure_history["ingame_minutes"] >= ingame_time - 60]
    pressure_history["Minutes Ago"] = ingame_time - pressure_history["ingame_minutes"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pressure_history["Minutes Ago"],
        y=pressure_history["CORE_PRESSURE"],
        mode="lines",
        line=dict(color="lightblue", width=2),
        name="Core Pressure"
    ))
    fig.add_hline(y=core_pressure_oper, line_dash="dash", line_color="green")
    fig.add_hline(y=core_pressure_max, line_dash="dash", line_color="red")

    fig.update_layout(
        paper_bgcolor="#2a2a2a",
        plot_bgcolor="#2a2a2a",
        font=dict(color="white"),
        height=350,
        margin=dict(t=30, b=30, l=50, r=20),
        xaxis_title="Minutes Ago",
        yaxis_title="Pressure (bar)",
        xaxis=dict(autorange="reversed"),
        yaxis=dict(range=[0, core_pressure_max + 50])
    )

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig, config={"displayModeBar": False}), width=12)
    ])

