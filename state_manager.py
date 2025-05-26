## state_manager.py
#
#import requests
#import threading
#
#GAME_URL = "http://localhost:8785"
#lock = threading.Lock()
#
#def get_variable(var):
#    try:
#        res = requests.get(f"{GAME_URL}/?Variable={var}", timeout=0.5)
#        res.raise_for_status()
#        text = res.text.strip().upper()
#        if not text:
#            return None
#        if text == "TRUE":
#            return 1.0
#        elif text == "FALSE":
#            return 0.0
#        try:
#            return float(text)
#        except ValueError:
#            return text
#    except requests.exceptions.RequestException:
#        return None
#
## Optional shared state (if needed later)
#shared_state = {
#    "core_temp_history": [],
#    "pressurizer_pressure_history": [],
#    "controllerUpdateTime": 0.0,
#}
