

# pyright: reportMissingTypeStubs=false

from controller import update_controller
from sim_api import fetch_simulator_data

from layout.All_Data_Tab import render_all_data_tab

from config import DEBUG_MODE
from dash import Dash, dcc, html, Output, Input, State, ctx, no_update
import dash_bootstrap_components as dbc


from layout.main_tab import render_main_tab
from layout.All_Data_Tab import render_all_data_tab
from layout.pressurizer_tab import render_pressurizer_tab
#from state_manager import get_variable


# Constants

FETCH_INTERVAL_MS = 1000  # Poll every 2 seconds

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], update_title=None, suppress_callback_exceptions=True)
app.title = "Nucleares Reactor Controller"
server = app.server

# Shared global data store
server.data = {}

#CORE_FACTOR = 14.154482083689501 -0.056352917328937525*RODS_POS_ACTUAL +0*COOLANT_CORE_CIRCULATION_PUMP_0_SPEED +0*COOLANT_CORE_CIRCULATION_PUMP_1_SPEED +0.0002587914581647562*COOLANT_CORE_CIRCULATION_PUMP_2_SPEED -0.033459251689966225 *CORE_IODINE_CUMULATIVE -0.10775036341414386*CORE_XENON_CUMULATIVE
# 1.5 iodine per thermal energy unit each tick i think
#seems xenon production is reduced above 420 degrees, with 520°C being the lowest ideal temp where xenon generation is reduced by 50%
#the "we dont generate any iodine" region would be: FACTOR <= BoronPPM/ 10800 


# Function to fetch all gettable variables and populate shared data

# App layout
def serve_layout():
    return html.Div([
        dcc.Store(id="controller-debug", data={}),
        html.H2("\u2699\ufe0f Reactor Autocontrol System", style={"margin": "10px"}),
        dcc.Tabs(id="tabs", value="main", children=[
            dcc.Tab(label="Main", value="main"),
            dcc.Tab(label="Pressurizer", value="pressurizer"),
            dcc.Tab(label="Primary Loop", value="primary"),
            dcc.Tab(label="Secondary Loop", value="secondary"),
            dcc.Tab(label="Condenser Loop", value="condenser"),
            dcc.Tab(label="All Data", value="AllData"),
        ]),
        html.Div(id="tab-content"),
        dcc.Interval(id="poll-interval", interval=FETCH_INTERVAL_MS, n_intervals=0),
            ])

app.layout = serve_layout

# Callback to sync controller toggle into server.data
@app.callback(
    Input("RodControllerToggle", "value")
)
def sync_controller_toggle(enabled):
    server.data["rod_controller_enable"] = int(bool(enabled))
    if DEBUG_MODE:
        print(f"[DEBUG] rod_controller_enable set to {server.data['rod_controller_enable']}")


# Callback: Update simulator data
@app.callback(
    Output("tab-content", "children"),
    Input("poll-interval", "n_intervals"),
    State("tabs", "value")
)
def poll_and_update(n, tab):
    print("")
    print("---------------------------------------")
    print(f"[DEBUG] Poll #{n} - Active Tab: {tab}")
    try:
        fetch_simulator_data(server.data)
    except Exception as e:
        import traceback
        print("[ERROR] Exception during fetch:")
        traceback.print_exc()
        return html.Div("⚠️ UI rendering error.")
    try:
        update_controller(server.data)
    except Exception as e:
        import traceback
        print("[ERROR] Exception during controller update:")
        traceback.print_exc()
        return html.Div("⚠️ UI rendering error.")
    #fetch_simulator_data(server.data)
    #try:
    #    update_controller(server.data)
    #except Exception as e:
    #    import traceback
    #    print("[ERROR] During controller update")
    #    traceback.print_exc()
    #
    #if DEBUG_MODE:
    #    keys = list(server.data.keys())
    #    print(f"[DEBUG] server.data has {len(keys)} keys: {keys[:5]}")

    try:
        match tab:
            case "main":        
                return render_main_tab(server.data)
            case "pressurizer":        
                return render_pressurizer_tab(server.data)
            case "AllData":
                return render_all_data_tab(server.data)
            case _:            
                return html.Div("Tab not implemented.")
    except Exception as e:
        import traceback
        print("[ERROR] Exception during render:")
        traceback.print_exc()
        return html.Div("⚠️ UI rendering error.")
    


import threading
import time

def background_controller_loop(data, interval_sec=0.5):
    while True:
        try:
            if DEBUG_MODE:
                print("Background Loop calling fetch simulator data")
            fetch_simulator_data(data)
            if DEBUG_MODE:
                print("Background Loop calling fetch simulator data")
            update_controller(data)
            #if DEBUG_MODE:
            #    print("[Background Controller] Tick")
            time.sleep(interval_sec)
        except Exception as e:
            import traceback
            print(f"[Controller Loop Error] {e}")
            traceback.print_exc()

if __name__ == "__main__":
    #threading.Thread(target=background_controller_loop, args=(server.data,), daemon=True).start()
    app.run(debug=True)
