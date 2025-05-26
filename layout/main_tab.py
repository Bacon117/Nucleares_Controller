# Filename: main_tab.py

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.graph_objs as go
import pandas as pd
import math
from config import DEBUG_MODE




boron_controller_state_labels = {
    0: "Off/Initialize",
    1: "Steady",
    2: "Increase PPM",
    3: "Decrease PPM",
    4: "PPM Limit Reached",
    5: "No Boron",
    6: "Core Not Reactive"
}

secondaryPump_controller_state_labels = {
    0: "Off/Initialize",
    1: "Hold",
    2: "Decrease",
    3: "Increase",
}

condenser_controller_state_labels = {
    0: "Initialize",
    1: "Hold",
    2: "Increase",
    3: "Decrease",
    4: "Max Pump Speed",
    5: "Pump Minimum",
    6: "Panic",
    100: "Disabled"
}

# === UI Configuration ===
UI_CONFIG = {
    "col_widths": {"chart": 6, "gauge": 3, "table": 3},
    "colors": {
        "bg": "#2a2a2a",
        "text": "white",
        "line": "cyan",
        "target": "green",
        "max": "red",
        "grid": "rgba(255, 255, 255, 0.05)",
        "axis": "#333",
        "border": "#333",
    },
    "chart": {
        "height": 350,
        "margin": dict(t=30, b=30, l=50, r=20),
        "xaxis_range": [0, 60],
        "xaxis_dtick": 10,
        "yaxis_buffer": 100
    }
}

# Persistent history
data_history = pd.DataFrame(columns=["ingame_minutes", "CORE_TEMP", "COOLANT_SEC_0_VOLUME", "COOLANT_SEC_1_VOLUME", "COOLANT_SEC_2_VOLUME"])
last_ingame_time = None

def get_controller_state_as_table(state):
    return html.Table([
        html.Thead(html.Tr([html.Th("Key"), html.Th("Value")]))
    ] + [
        html.Tr([html.Td(str(k)), html.Td(str(v))]) for k, v in state.items()
    ], style={"fontSize": "12px", "color": "white", "borderCollapse": "collapse", "border": "1px solid #888"})

def make_row(label, value, background_color, text_color="lightgray"):
    return html.Tr([
        html.Td(label, style={"background": background_color, "color": text_color}),
        html.Td(value, style={"background": background_color, "color": text_color})
    ])

def render_main_tab(data):
    global data_history, last_ingame_time

    if not data:
        if DEBUG_MODE:
            print("[Core_tab DEBUG] render_core_tab received empty data")
        return html.Div("Waiting for data...")

    if DEBUG_MODE:
        print(f"[Core Tab DEBUG] CORE_TEMP: {data.get('CORE_TEMP')}, TIME_STAMP: {data.get('TIME_STAMP')}")

    # One-liner validated inputs
    core_temp = data.get("CORE_TEMP", -1)
    core_temp_max = data.get("CORE_TEMP_MAX", -1)
    core_temp_target = data.get("core_temp_target", 0)
    core_criticality = float(data.get("CORE_STATE_CRITICALITY", -1.0) or -1.0)
    ingame_time = data.get("TIME_STAMP", -1)
    
    rod_actuals = [data.get(f"ROD_BANK_POS_{i}_ACTUAL", -1) for i in range(9)]
    rod_ordered = [data.get(f"ROD_BANK_POS_{i}_ORDERED", -1) for i in range(9)]
    rod_controller = [data.get(f"ROD_BANK_POS_{i}_CONTROLLER", -1) for i in range(9)]
    
    COOLANT_SEC_0_VOLUME = data.get("COOLANT_SEC_0_VOLUME", -1)
    COOLANT_SEC_1_VOLUME = data.get("COOLANT_SEC_1_VOLUME", -1)
    COOLANT_SEC_2_VOLUME = data.get("COOLANT_SEC_2_VOLUME", -1)
    
    secondary_loop0_controller_state = data.get("secondary_loop0_controller_state", -1)
    secondary_loop1_controller_state = data.get("secondary_loop1_controller_state", -1)
    secondary_loop2_controller_state = data.get("secondary_loop2_controller_state", -1)
    
    COOLANT_SEC_CIRCULATION_PUMP_0_ORDERED_SPEED = data.get("COOLANT_SEC_CIRCULATION_PUMP_0_ORDERED_SPEED", -1)
    COOLANT_SEC_CIRCULATION_PUMP_1_ORDERED_SPEED = data.get("COOLANT_SEC_CIRCULATION_PUMP_1_ORDERED_SPEED", -1)
    COOLANT_SEC_CIRCULATION_PUMP_2_ORDERED_SPEED = data.get("COOLANT_SEC_CIRCULATION_PUMP_2_ORDERED_SPEED", -1)
    
    GENERATOR_0_KW = data.get("GENERATOR_0_KW", 0)
    GENERATOR_1_KW = data.get("GENERATOR_1_KW", 0)
    GENERATOR_2_KW = data.get("GENERATOR_2_KW", 0)
    GeneratedPower_MW = (GENERATOR_0_KW + GENERATOR_1_KW + GENERATOR_2_KW) / 1000
    
    POWER_DEMAND_MW = data.get("POWER_DEMAND_MW", -1)
    
    boron_controller_state = data.get("boron_controller_state", -1)
    boron_ppm = data.get("CHEM_BORON_PPM"),-1
    
    condenser_temperature = data.get("CONDENSER_TEMPERATURE",0)

    # Update temperature history
    data_history = pd.concat([
        data_history,
        pd.DataFrame({
            "ingame_minutes": [ingame_time],
            "CORE_TEMP": [core_temp],
            "COOLANT_SEC_0_VOLUME": [COOLANT_SEC_0_VOLUME],
            "COOLANT_SEC_1_VOLUME": [COOLANT_SEC_1_VOLUME],
            "COOLANT_SEC_2_VOLUME": [COOLANT_SEC_2_VOLUME]
        })
    ], ignore_index=True)

    if last_ingame_time is None or ingame_time > last_ingame_time:
        data_history = data_history[data_history["ingame_minutes"] >= ingame_time - 60]
        last_ingame_time = ingame_time

    data_history["Minutes Ago"] = (ingame_time - data_history["ingame_minutes"]).clip(lower=0, upper=60)
    
    # === Components ===
    
    rows = [
    ("Core Temp °C", f"{data.get('CORE_TEMP', -1):.2f}", "rgba(255, 193, 7, 0.2)"),
    ("Core Temp Target °C", f"{data.get('core_temp_target', -1):.2f}", "rgba(255, 193, 7, 0.2)"),
    ("Core Temp CE", f"{data.get('core_temp_control_effort', -1):.2f}", "rgba(255, 193, 7, 0.2)"),
    ("Rod Rate %/m", f"{data.get('reactivity_control_effort', -1):.2f}", "rgba(40, 167, 69, 0.2)"),
    ("React Target Max", f"{data.get('reactivity_request_gain', -1):.2f}", "rgba(40, 167, 69, 0.2)"),
    (f"SG Pump L1 [{COOLANT_SEC_CIRCULATION_PUMP_0_ORDERED_SPEED:.0f}]", secondaryPump_controller_state_labels.get(secondary_loop0_controller_state, "Error"), "rgba(23, 162, 184, 0.2)"),
    (f"SG Pump L2 [{COOLANT_SEC_CIRCULATION_PUMP_1_ORDERED_SPEED:.0f}]", secondaryPump_controller_state_labels.get(secondary_loop1_controller_state, "Error"), "rgba(23, 162, 184, 0.2)"),
    (f"SG Pump L3 [{COOLANT_SEC_CIRCULATION_PUMP_2_ORDERED_SPEED:.0f}]", secondaryPump_controller_state_labels.get(secondary_loop2_controller_state, "Error"), "rgba(23, 162, 184, 0.2)"),
    ("boron_controller_state", boron_controller_state_labels.get(boron_controller_state, "Error"), "rgba(220, 53, 69, 0.2)"),
    ("Born PPM", f"{data.get('CHEM_BORON_PPM', -1):.2f}", "rgba(220, 53, 69, 0.2)"),
    (f"Pump D1 [{data.get('CONDENSER_CIRCULATION_PUMP_SPEED', -1):.0f}]", f"({int(condenser_temperature)} °C) {condenser_controller_state_labels.get(data.get('condenser_controller_state', -1), 'Error')}", "rgba(108, 117, 125, 0.2)")
    ]

    TempControllerVariables = dbc.Card([       
        dbc.CardHeader("Temp Controller Variables"),
        dbc.CardBody([
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Name", style={"width": "50%"}),
                    html.Th("Value", style={"width": "50%"})
                ])),
                html.Tbody([make_row(label, value, background_color) for label, value, background_color in rows])
            ], bordered=True, hover=True, size="sm", className="table-dark")
        ])
    ], className="bg-dark border-secondary shadow-sm mb-3")

     
    PowerLCD = daq.LEDDisplay(
            id='Generated_Power_MW_LCD',
            label="Generating",
            
            #value=f"{int(GeneratedPower_MW):>4}",
            #value = str(int(GeneratedPower_MW)),
            #value=str(int(GeneratedPower_MW)).rjust(4),
            value=str(int(GeneratedPower_MW)).zfill(4),
            color="Red",
            #backgroundColor="gray",
            backgroundColor="rgba(0,0,0,0)",
            size=64,
            #style={"border": "2px solid #00FF00", "borderRadius": "5px", "padding": "10px"}
        ),
    DemandLCD = daq.LEDDisplay(
            id='Demand Power',
            label="Demand",
            value=str(int(POWER_DEMAND_MW)).zfill(4),
            color="Green",
            backgroundColor="rgba(0,0,0,0)",
            size=64,
            #style={"border": "2px solid #00FF00", "borderRadius": "5px", "padding": "10px"}
        ), 
     
    Gen1_LCD = daq.LEDDisplay(
            id='Gen1 Power',
            label="Gen1 MW",
            labelPosition = "Left",
            value=str(int(GENERATOR_0_KW/1000)).zfill(4),
            color="Yellow",
            backgroundColor="rgba(0,0,0,0)",
            size=18,
            #style={"border": "2px solid #00FF00", "borderRadius": "5px", "padding": "10px"}
        ), 
     
    Gen2_LCD = daq.LEDDisplay(
            id='Gen2 Power',
            label="Gen2 MW",
            labelPosition = "Left",
            value=str(int(GENERATOR_1_KW/1000)).zfill(4),
            color="Yellow",
            backgroundColor="rgba(0,0,0,0)",
            size=18,
            #style={"border": "2px solid #00FF00", "borderRadius": "5px", "padding": "10px"}
        ), 
    
    Gen3_LCD = daq.LEDDisplay(
            id='Gen3 Power',
            label="Gen3 MW",
            labelPosition = "Left",
            value=str(int(GENERATOR_2_KW/1000)).zfill(4),
            color="Yellow",
            backgroundColor="rgba(0,0,0,0)",
            size=18,
            #style={"border": "2px solid #00FF00", "borderRadius": "5px", "padding": "10px"}
        ), 
    
    
    
    
    
    
    ReactivtyControllerVariables = dbc.Card([
        dbc.CardHeader("Reactivity Controller Variables"),
        dbc.CardBody([
            dbc.Table([
                html.Thead(html.Tr([html.Th("Name"), html.Th("Value")])),
                html.Tbody([
                    #html.Tr([html.Td("CORE_STATE_CRITICALITY")          ,html.Td(f"{data.get("CORE_STATE_CRITICALITY"          ,-1):.2f}")]),
                    #html.Tr([html.Td("reactivity_control_error")        ,html.Td(f"{data.get("reactivity_control_error"        ,-1):.2f}")]),
                    #html.Tr([html.Td("reactivity_controller_lowerLim")  ,html.Td(f"{data.get("reactivity_controller_lowerLim"  ,-1):.2f}")]),
                    #html.Tr([html.Td("reactivity_request_gain")         ,html.Td(f"{data.get("reactivity_request_gain"         ,-1):.2f}")]),
                    #html.Tr([html.Td("reactivity_controller_gain")      ,html.Td(f"{data.get("reactivity_controller_gain"      ,-1):.2f}")]),
                    #html.Tr([html.Td("reactivity_controller_upperLim")  ,html.Td(f"{data.get("reactivity_controller_upperLim"  ,-1):.2f}")]),
                    #
                ])
            ], bordered=True, hover=True, size="sm", className="table-dark")
        ])
    ], className="bg-dark border-secondary shadow-sm mb-3")





    rod_table = dbc.Card([
        dbc.CardBody([
            dbc.Table([
                html.Thead(html.Tr([html.Th("Bank"), html.Th("Actual"), html.Th("Ordered"), html.Th("Controller")])),
                html.Tbody([
                    html.Tr([
                        html.Td(f"Bank {i}"),
                        html.Td(f"{rod_actuals[i]:.2f}" if isinstance(rod_actuals[i], (int, float)) and rod_actuals[i] >= 0 else "--"),
                        html.Td(f"{rod_ordered[i]:.2f}" if isinstance(rod_ordered[i], (int, float)) and rod_ordered[i] >= 0 else "--"),
                        html.Td(f"{rod_controller[i]:.2f}" if isinstance(rod_controller[i], (int, float)) and rod_controller[i] >= 0 else "--")
                    ]) for i in range(9)
                ])
            ], bordered=True, hover=True, size="sm", className="table-dark")
        ])
    ], className="bg-dark border-secondary shadow-sm")

    reactivity_gauge = dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div(style={
                    'width': '14px', 'height': '14px', 'borderRadius': '7px',
                    'backgroundColor': "#ff0000" if data.get("CORE_CRITICAL_MASS_REACHED") else "#222222",
                    'display': 'inline-block', 'marginRight': '8px', 'verticalAlign': 'middle'
                }),
                html.Span("Critical Mass", style={'color': UI_CONFIG["colors"]["text"], 'fontSize': '12px'})
            ], style={'marginBottom': '10px'}),
            dcc.Graph(figure=go.Figure(go.Indicator(
                mode="gauge+number",
                value=core_criticality,
                title={"text": "Reactivity"},
                gauge={
                    "axis": {"range": [-0.5, 0.5]},
                    "bar": {"color": UI_CONFIG["colors"]["text"]},
                    "steps": [
                        {"range": [-0.5, -0.2], "color": "red"},
                        {"range": [-0.2, -0.1], "color": "yellow"},
                        {"range": [-0.1, 0.1], "color": "green"},
                        {"range": [0.1, 0.2], "color": "yellow"},
                        {"range": [0.2, 0.5], "color": "red"}
                    ]
                }
            )).update_layout(
                paper_bgcolor=UI_CONFIG["colors"]["bg"],
                font=dict(color=UI_CONFIG["colors"]["text"]),
                height=315
            ), config={"displayModeBar": False})
        ])], className="bg-dark border-secondary shadow-sm")

    reactivity_gauge2 = dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div(style={
                    'width': '14px', 'height': '14px', 'borderRadius': '7px',
                    'backgroundColor': "#ff0000" if data.get("CORE_CRITICAL_MASS_REACHED") else "#222222",
                    'display': 'inline-block', 'marginRight': '8px', 'verticalAlign': 'middle'
                }),
                html.Span("Critical Mass", style={'color': UI_CONFIG["colors"]["text"], 'fontSize': '12px'})
            ], style={'marginBottom': '0px'}),
            daq.Gauge(
                color={
                    "gradient":False,
                    "ranges":{
                        "red":[-0.5,-0.2],
                        "yellow":[-0.2,-0.1],
                        "green":[-0.1,0.1],
                        "#FFFF00":[0.1,0.2],
                        "#FF0000":[0.2,0.5]
                    }
                    
                },
                #value = core_criticality,
                #value=f"{core_criticality:.3f}",
                value=round(core_criticality, 2),
                max=0.5,
                min=-0.5,
                showCurrentValue=True,
                label = "Reactivity",
                digits=2,
                size=250,
                style={
                    "marginBottom": "-45px",
                    #'border': '2px solid black',
                    #'padding': '0px',
                    #'display': 'flex',
                    #'borderRadius': '10px'
                }   
            )
        ])], className="bg-dark border-secondary shadow-sm")

    y_axis_max = ((max(core_temp, core_temp_max) + UI_CONFIG["chart"]["yaxis_buffer"] - 1) // UI_CONFIG["chart"]["yaxis_buffer"]) * UI_CONFIG["chart"]["yaxis_buffer"]

    temp_chart = dbc.Card([
        dbc.CardBody([
            dcc.Graph(figure=go.Figure([
                go.Scatter(
                    x=-data_history["Minutes Ago"],
                    y=data_history["CORE_TEMP"],
                    mode="lines",
                    line=dict(color=UI_CONFIG["colors"]["line"], width=2),
                    name="Core Temp"
                )
            ]).add_hline(y=core_temp_target, line_dash="dash", line_color=UI_CONFIG["colors"]["target"])
              .add_hline(y=core_temp_max, line_dash="dash", line_color=UI_CONFIG["colors"]["max"])
              .update_layout(
                title = "Core Temperature",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=UI_CONFIG["colors"]["text"]),
                height=UI_CONFIG["chart"]["height"],
                margin=UI_CONFIG["chart"]["margin"],
                xaxis_title="Δt (minutes)",
                yaxis_title="Temp (°C)",
                yaxis=dict(
                    range=[0, y_axis_max],
                    gridcolor=UI_CONFIG["colors"]["grid"],
                    linecolor=UI_CONFIG["colors"]["axis"],
                    mirror=True
                ),
                xaxis=dict(
                    autorange=False,
                    linecolor=UI_CONFIG["colors"]["axis"],
                    mirror=True,
                    range=[-60, 0],
                    dtick=UI_CONFIG["chart"]["xaxis_dtick"],
                    gridcolor=UI_CONFIG["colors"]["grid"]
                )
            ), config={"displayModeBar": False})
        ])], className="bg-dark border-secondary shadow-sm")
    
    
    # Calculate dynamic y-axis upper limit
    max_y_value = max(
        data_history["COOLANT_SEC_0_VOLUME"].max(),
        data_history["COOLANT_SEC_1_VOLUME"].max(),
        data_history["COOLANT_SEC_2_VOLUME"].max()
    )
   


    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
    y_axis_upper_limit = max(50000, max_y_value + 10000)
    
    sec_volume_chart = dbc.Card([
        dbc.CardBody([
            dcc.Graph(figure=go.Figure([
                go.Scatter(
                    x=-data_history["Minutes Ago"],
                    y=data_history["COOLANT_SEC_2_VOLUME"],
                    mode="lines",
                    line=dict(color="orange", width=2),
                    name="Loop 3"
                ),
                go.Scatter(
                    x=-data_history["Minutes Ago"],
                    y=data_history["COOLANT_SEC_1_VOLUME"],
                    mode="lines",
                    line=dict(color="cyan", width=2),
                    name="Loop 2"
                ),
                go.Scatter(
                    x=-data_history["Minutes Ago"],
                    y=data_history["COOLANT_SEC_0_VOLUME"],
                    mode="lines",
                    line=dict(color="magenta", width=2),
                    name="Loop 1"
                )
            ]).add_hline(y=30000, line_dash="dash", line_color="green")
            .add_hline(y=45000, line_dash="dash", line_color="red")
            .add_hline(y=15000, line_dash="dash", line_color="red")
            .update_layout(
                title="Steam Gen Volume",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=UI_CONFIG["colors"]["text"]),
                height=UI_CONFIG["chart"]["height"],
                margin=UI_CONFIG["chart"]["margin"],
                xaxis_title="Δt (minutes)",
                yaxis_title="Volume (L)",
                yaxis=dict(
                    range=[0, y_axis_upper_limit],
                    gridcolor=UI_CONFIG["colors"]["grid"],
                    linecolor=UI_CONFIG["colors"]["axis"],
                    mirror=True
                ),
                xaxis=dict(
                    autorange=False,
                    linecolor=UI_CONFIG["colors"]["axis"],
                    mirror=True,
                    range=[-60, 0],
                    dtick=UI_CONFIG["chart"]["xaxis_dtick"],
                    gridcolor=UI_CONFIG["colors"]["grid"]
                )
            ), config={"displayModeBar": False})
        ])
    ], className="bg-dark border-secondary shadow-sm")

    status_panel = dbc.Row([
        dbc.Col(html.Div(
            f"System Online | Day {int(ingame_time // (24 * 60))}, {int(ingame_time % (24 * 60) // 60):02d}:{int(ingame_time % 60):02d}",
            className="text-muted small ms-2 mb-2"
        ), width=12)])

    rod_control_card = dbc.Card([
        dbc.CardBody([
            html.Div("Set Rod Position (%):", className="text-white mb-2"),
            dcc.Input(id="rod-command-input", type="number", min=0, max=100, step=0.1,
                      placeholder="Enter 0-100", value=100, persistence=True, persistence_type='session'),
            dbc.Button("Set Position", id="rod-command-btn", color="primary", className="mt-2"),
            dbc.Switch(id = "RodControllerToggle", label = "Enable Rod Controller", value = data.get("rod_controller_enable") or 0,className = "mb-3")
        ])], className="bg-dark border-secondary shadow-sm")




    

    
    #data["rod_controller_enable"] = 1 if data.get("RodControllerToggle") else 0
    
    
    
    return dbc.Container([
        
        html.Div(id="controller-debug-panel", style={"position": "absolute", "bottom": 10, "right": 10, "color": "white", "fontSize": "12px"}),
        #html.Div(get_display_components("Core"), style={"position": "absolute", "bottom": 10, "right": 10, "color": "white", "fontSize": "12px"}),
        status_panel,
        dbc.Row([
            dbc.Col(PowerLCD, style={"flex": "0"}),
            dbc.Col(DemandLCD, style={"flex": "0"}),
            dbc.Col(Gen1_LCD, style={"flex": "0","position": "relative","top": "30px"}),             
            dbc.Col(Gen2_LCD, style={"flex": "0","position": "relative","top": "30px"}),             
            dbc.Col(Gen3_LCD, style={"flex": "0","position": "relative","top": "30px"}),             
            ], style={"display": "flex"}, className="dark-theme-control"),
        #dbc.Row([
        #    dbc.Col(PowerLCD, style={"flex": "0"}),
        #    dbc.Col(DemandLCD, style={"flex": "0"}),
        #    dbc.Col(html.Div([Gen1_LCD, Gen2_LCD, Gen3_LCD]))
        #], style={"display": "flex"},className="dark-theme-control"),
        #dbc.Row([dbc.Col(PowerLCD,width=2),
        #    dbc.Col(DemandLCD,width=2)
        #]),
        #col wids sum to 12 or less
        dbc.Row([
            dbc.Col(temp_chart, md=5),
            dbc.Col(reactivity_gauge2, md=3),           
            dbc.Col(rod_table, md=3)            
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(sec_volume_chart, md = 5),
            dbc.Col(rod_control_card, md=3),
            dbc.Col(TempControllerVariables, md=2),
            dbc.Col(ReactivtyControllerVariables, md=2)
        ], className="mb-4")
    ], fluid=True)
