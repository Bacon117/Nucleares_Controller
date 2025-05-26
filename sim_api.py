import requests, time, csv, os
from datetime import datetime, timezone
from typing import Any

from config import DEBUG_MODE

SIMULATOR_URL = "http://localhost:8785"
MinRequestInterval_ms = 2000

key_variables = ("CORE_STATE_CRITICALITY","GENERATOR_0_KW","GENERATOR_1_KW","GENERATOR_2_KW")

log_variables = ["CORE_STATE_CRITICALITY", "CORE_FACTOR", "CORE_INTEGRITY", "CORE_IODINE_CUMULATIVE","CORE_IODINE_GENERATION","CORE_XENON_CUMULATIVE","CORE_XENON_GENERATION","CORE_TEMP","CORE_STATE_CRITICALITY"]

def persist_data_snapshot(data:dict[Any,Any], path: str ="C:\\Users\\Rsenior\\Documents\\NuclearesDataRepo\\simulator_data_log.csv"):
    try:
        snapshot_time = datetime.now(timezone.utc).isoformat()
        file_exists = os.path.isfile(path)

        headers = ["timestamp"] + log_variables

        # Check if file exists and if headers are mismatched
        recreate_file = True
        if file_exists:
            with open(path, "r", newline='') as f:
                reader = csv.reader(f)
                existing_headers = next(reader)
                if existing_headers == headers:
                    recreate_file = False

        if recreate_file:
            with open(path, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

        row = {var: data.get(var, 'NaN') for var in log_variables}
        row["timestamp"] = snapshot_time

        with open(path, "a", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow(row)

    except Exception as e:
        print(f"[ERROR] Failed to write snapshot: {e}")

def fetch_simulator_data(data:dict[Any,Any]):
    persist_data_snapshot(data)
    print("[NewFetch] start")
    lastfetch_ms = data.get("lastfetch_ms") or 0
    IRLtime_ms = int(time.time()*1000)

    # Always fetch key variables
    for var in key_variables:
        try:
            val_resp = requests.get(f"{SIMULATOR_URL}/?Variable={var}")
            value = val_resp.text.strip()
            print(f"var: {var} value: {value}")
            data[var] = float(value) if value.replace('.', '', 1).isdigit() else value
        except Exception:
            import traceback
            print(f"[ERROR] Exception during key variable fetch: {var}")
            traceback.print_exc()

    if IRLtime_ms - lastfetch_ms > MinRequestInterval_ms:
        data["lastfetch_ms"] = IRLtime_ms
        try:
            response = requests.get(f"{SIMULATOR_URL}/?Variable=WEBSERVER_LIST_VARIABLES")
        except Exception as e:
            import traceback
            print("[ERROR] Exception during fetching list variables:")
            traceback.print_exc()
            print(f"ErrorName: {e}")
            return

        text = response.text.strip()
        get_line = next(line for line in text.splitlines() if line.startswith("GET:"))
        variable_list = get_line.replace("GET:", "").split(',')

        fetch_error = 0

        for var in variable_list:
            try:
                val_resp = requests.get(f"{SIMULATOR_URL}/?Variable={var}")
                time.sleep(0.010)
                value = val_resp.text.strip()
                data[var] = float(value) if value.replace('.', '', 1).isdigit() else value
            except:
                fetch_error += 1
                import traceback
                print("[ERROR] Exception during render:")
                traceback.print_exc()

        if fetch_error > 0:
            print(f"⚠  {fetch_error} ERRORS DURING FETCH   ⚠")



def set_game_variable(var:str, value:Any):
    try:
        post_url = f"{SIMULATOR_URL}/?variable={var}&value={value}"
        res = requests.post(post_url)
        res.raise_for_status()
        if DEBUG_MODE:
            print(f"✅ Set {var} = {value}")
        return True
    except Exception as e:
        if DEBUG_MODE:
            print(f"❌ Failed to set {var}: {e}")
        return False
