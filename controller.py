from sim_api import set_game_variable
from controllers.SecondaryLoop import update_secondary_loop_controllers
from typing import Any, Dict

# Shared registry to track UI variable displays
#_display_registry = {}


ENABLE     = 0x100000
RODHI      = 0x010000
RODLO      = 0x001000
PPMLIM     = 0x000100
NOBORON    = 0x000010
COREACTIVE = 0x000001













#def DisplayVar(value, tab_name, label=None):
#    from dash import html
#    label = label or str(value)
#    if tab_name not in _display_registry:
#        _display_registry[tab_name] = {}
#    _display_registry[tab_name][label] = html.Div(f"{label}: {value}")

#def get_display_components(tab_name):
#    return list(_display_registry.get(tab_name, {}).values())

def update_controller(data: Dict[str, Any]) -> None:
    print("Update Controller")
    data.setdefault("rod_controller_enable", 1)
    data["secondary_pump_controller0_enable"] = 0
    data["secondary_pump_controller1_enable"] = 1
    data["secondary_pump_controller2_enable"] = 1
    data["boron_controller_enable"] = 1
    data["condenser_controller_enable"] = 1
    data["rod_equilize"] = 1

    update_core_temp_and_reactivity(data)
    update_rod_controller(data)
    update_secondary_loop_controllers(data)
    update_boron_dosing_controller(data)
    update_condenser_controller(data)

    try:
        data["MSCV loop2 DeltaP"] = (data.get("COOLANT_SEC_1_PRESSURE", 0) or 0) - (data.get("STEAM_TURBINE_1_PRESSURE", 0) or 0)
    except Exception:
        data["MSCV loop2 DeltaP"] = -1

    try:
        valve_percent = data.get("MSCV_2_OPENING_ACTUAL", 0) or 0
        expected_rate = 10 * valve_percent
        sg_mass_out = data.get("STEAM_GEN_2_OUTLET", 0) or 0
        T = data.get("STEAM_TURBINE_2_TEMPERATURE", 0) or 0
        h_in = 2504 + 1.89 * T
        h_out = h_in - 590
        Demand_MW = data.get("POWER_DEMAND_MW", 0) or 0
        if h_in - h_out > 0.001:
            mass_req = Demand_MW * (300 / 179)
        else:
            mass_req = 0
        throttle_val = -1
        if expected_rate > 0.1:
            throttle_val = 1 - (sg_mass_out / expected_rate)
        data["z_Mass_Required"] = mass_req
        data["z_Loop 3 Mass Rate Expected"] = expected_rate
        data["z_Loop 3 MSCV Throttle"] = throttle_val
    except Exception:
        data["z_Loop 3 MSCV Throttle"] = -1

    data["controller_last_update"] = data.get("TIME_STAMP", 0) or 0
    return

# === Extracted Controllers ===

def update_core_temp_and_reactivity(data: Dict[str, Any]) -> None:
    core_temp = data.get("CORE_TEMP", 0) or 0
    core_criticality = float(data.get("CORE_STATE_CRITICALITY", 0) or 0)

    core_temp_target = 350
    core_temp_controller_gain = 1 / 20
    core_temp_controller_upperLim = 1
    core_temp_controller_lowerLim = -1
    core_temp_target_deadband = 1

    core_temp_error = core_temp_target - core_temp
    core_temp_control_effort = core_temp_error * core_temp_controller_gain
    core_temp_control_effort = max(core_temp_controller_lowerLim, min(core_temp_controller_upperLim, core_temp_control_effort))
    core_temp_control_effort = core_temp_control_effort if abs(core_temp - core_temp_target) > core_temp_target_deadband else 0

    reactivity_request_gain = 0.25
    reactivity_controller_gain = 1
    reactivity_controller_upperLim = 0.4
    reactivity_controller_lowerLim = -0.15

    reactivity_request = core_temp_control_effort * reactivity_request_gain
    reactivity_control_error = core_criticality - reactivity_request
    reactivity_control_effort = reactivity_control_error * reactivity_controller_gain
    reactivity_control_effort = max(reactivity_controller_lowerLim, min(reactivity_controller_upperLim, reactivity_control_effort))
    reactivity_control_effort = round(reactivity_control_effort, 2)

    data.update({
        "core_temp_controller_gain": core_temp_controller_gain,
        "core_temp_controller_upperLim": core_temp_controller_upperLim,
        "core_temp_controller_lowerLim": core_temp_controller_lowerLim,
        "core_temp_error": core_temp_error,
        "core_temp_target": core_temp_target,
        "core_temp_control_effort": core_temp_control_effort,
        "reactivity_request_gain": reactivity_request_gain,
        "reactivity_controller_gain": reactivity_controller_gain,
        "reactivity_controller_upperLim": reactivity_controller_upperLim,
        "reactivity_controller_lowerLim": reactivity_controller_lowerLim,
        "reactivity_control_error": reactivity_control_error,
        "reactivity_control_effort": reactivity_control_effort
    })

def update_rod_controller(data: Dict[str, Any]) -> None:
    ingame_time = data.get("TIME_STAMP", 0) or 0
    delta_minutes = ingame_time - (data.get("controller_last_update", ingame_time) or ingame_time)
    reactivity_control_effort = data.get("reactivity_control_effort", 0) or 0
    rod_actuals: list[float] = []

    if data.get("rod_controller_enable", 0):
        for i in range(9):
            try:
                actual = data.get(f"ROD_BANK_POS_{i}_ACTUAL", 0)
                if isinstance(actual, float):
                    rod_actuals.append(actual)
                    commanded = round(actual + reactivity_control_effort * delta_minutes, 2)
                    data[f"ROD_BANK_POS_{i}_CONTROLLER"] = commanded
                    if round(commanded, 2) != round(actual, 2):
                        set_game_variable(f"ROD_BANK_POS_{i}_ORDERED", commanded)
                    else:
                        print(f"No rod update, request too close, bank: {i+1}")
            except Exception:
                import traceback
                print("[ERROR] Exception setting rod controller command")
                traceback.print_exc()
        if data.get("rod_equilize", 0):
            print("poop")


def boron_state_transition(state_transition_variable: int) -> int:
    if not (state_transition_variable & ENABLE):
        state = 0
    elif not (state_transition_variable & COREACTIVE):
        state = 6
    elif state_transition_variable & PPMLIM:
        state = 4
    elif state_transition_variable & NOBORON:
        state = 5
    elif state_transition_variable & RODHI:
        state = 2
    elif state_transition_variable & RODLO:
        state = 3
    else:
        state = 1
    return state

def update_boron_dosing_controller(data: Dict[str, Any]) -> None:
    print("")
    print("Starting Boron dosing controller")
    ingame_time = data.get("TIME_STAMP", 0) or 0
    boron_update_InGameMinutes = 1
    rod_upper_limit = 60
    rod_lower_limit = 50
    boron_rate_increase = 10
    boron_filter_speed = 10
    boron_PPM_limit = 3000

    boron_controller_enable = data.get("boron_controller_enable", 0) or 0
    state = data.get("boron_controller_state", 0) or 0
    RODS_POS_ACTUAL = data.get("RODS_POS_ACTUAL", -1) or -1
    boron_ppm = data.get("CHEM_BORON_PPM", -1) or -1
    last_boron_update_time = data.get("last_boron_update_time", 0) or 0
    core_state = data.get("CORE_STATE", 0)

    state_transition_variable = 0
    if boron_controller_enable:
        state_transition_variable |= ENABLE
    if RODS_POS_ACTUAL <= 0:
        state_transition_variable &= ~ENABLE
    if RODS_POS_ACTUAL > rod_upper_limit:
        state_transition_variable |= RODHI
    if RODS_POS_ACTUAL < rod_lower_limit:
        state_transition_variable |= RODLO
    if boron_ppm > boron_PPM_limit:
        state_transition_variable |= PPMLIM
    if boron_ppm <= 0.01:
        state_transition_variable |= NOBORON
    if core_state == "REACTIVO":
        state_transition_variable |= COREACTIVE

    print(f"Ingame Time {ingame_time}")
    print(f"Last Boron Update Time {last_boron_update_time}")
    if int(ingame_time - last_boron_update_time) < int(boron_update_InGameMinutes):
        print("Not Time to update boron controller")
        return
    data["last_boron_update_time"] = ingame_time
    print(f"🟡State: {state}")
    print(f"Transition Variable: {state_transition_variable:06b}")
    match state:
        case 0:  # Initialize/OFF
            print("State 0")
            if state_transition_variable & ENABLE:
                state = 1
            else:
                state = 0
        case 1:  # Hold
            set_game_variable("CHEM_BORON_DOSAGE_ORDERED_RATE", 0)
            set_game_variable("CHEM_BORON_FILTER_ORDERED_SPEED", 0)
            state = boron_state_transition(state_transition_variable)
        case 2:  # increase boron
            set_game_variable("CHEM_BORON_DOSAGE_ORDERED_RATE", boron_rate_increase)
            set_game_variable("CHEM_BORON_FILTER_ORDERED_SPEED", 0)
            state = boron_state_transition(state_transition_variable)
        case 3:  # decrease boron
            set_game_variable("CHEM_BORON_DOSAGE_ORDERED_RATE", 0)
            set_game_variable("CHEM_BORON_FILTER_ORDERED_SPEED", boron_filter_speed)
            state = boron_state_transition(state_transition_variable)
        case 4:  # Boron PPM Lim
            set_game_variable("CHEM_BORON_DOSAGE_ORDERED_RATE", 0)
            set_game_variable("CHEM_BORON_FILTER_ORDERED_SPEED", 0)
            state = boron_state_transition(state_transition_variable)
        case 5:  # no boron
            state = boron_state_transition(state_transition_variable)
        case 6:  # core not reactive
            state = boron_state_transition(state_transition_variable)
        case _:
            pass
    data["boron_controller_state"] = state

def update_condenser_controller(data: Dict[str, Any]) -> None:
    print("Start Update Condenser")
    ingame_time = data.get("TIME_STAMP", 0) or 0
    
    condenser_temp = data.get("CONDENSER_TEMPERATURE", 0)
    current_speed = data.get("CONDENSER_CIRCULATION_PUMP_SPEED", 0) or 0
    state = data.get("condenser_controller_state", 0)
    enable = data.get("condenser_controller_enable", 0)
    last_decrease_time = data.get("last_decrease_time", 0) or 0

    condenser_temp_target = 103
    condenser_temp_deadband = 3
    condenser_temp_critical = 108
    condenser_pump_max_speed = 100
    condenser_pump_min_speed = 5
    if enable:
        print("Condenser Enabled")
        if condenser_temp is None:
            data["condenser_controller_state"] = -1
            print("No condenser temp")
            return
        # state transition variable
        TEMP_HIGH = 0x10000
        TEMP_LOW = 0x01000
        PUMP_MAX = 0x00100
        PUMP_MIN = 0x00010
        CRIT_TEMP = 0x00001

        state_transition = 0
        if condenser_temp > condenser_temp_target + condenser_temp_deadband:
            state_transition |= TEMP_HIGH
        if condenser_temp < condenser_temp_target - condenser_temp_deadband:
            state_transition |= TEMP_LOW
        if int(current_speed) == int(condenser_pump_max_speed):
            state_transition |= PUMP_MAX
        if int(current_speed) == int(condenser_pump_min_speed):
            state_transition |= PUMP_MIN
        if condenser_temp >= condenser_temp_critical:
            state_transition |= CRIT_TEMP

        print("Running condenser state calcs")
        print(f"State: {state}")
        match state:
            case 0:  # Initialize
                print("State 0")
                state = 1
            case 1:  # Hold
                print("State 1")
                if state_transition & CRIT_TEMP:
                    state = 6
                elif state_transition & PUMP_MAX:
                    state = 4
                elif state_transition & PUMP_MIN:
                    state = 5
                elif state_transition & TEMP_HIGH:
                    state = 2
                elif state_transition & TEMP_LOW:
                    state = 3
                else:
                    state = 1
            case 2:  # Increase
                print("State 2")
                new_speed = max(min(current_speed + 1, condenser_pump_max_speed), condenser_pump_min_speed)
                set_game_variable("CONDENSER_CIRCULATION_PUMP_ORDERED_SPEED", new_speed)
                if state_transition & CRIT_TEMP:
                    state = 6
                elif state_transition & PUMP_MAX:
                    state = 4
                elif state_transition & PUMP_MIN:
                    state = 2
                elif state_transition & TEMP_HIGH:
                    state = 2
                elif state_transition & TEMP_LOW:
                    state = 3
                else:
                    state = 1
            case 3:  # Decrease
                print("State 3")
                new_speed = max(min(current_speed - 1, condenser_pump_max_speed), condenser_pump_min_speed)
                if int(ingame_time - last_decrease_time) > 2:
                    data["last_decrease_time"] = ingame_time
                    set_game_variable("CONDENSER_CIRCULATION_PUMP_ORDERED_SPEED", new_speed)
                if state_transition & CRIT_TEMP:
                    state = 6
                elif state_transition & PUMP_MAX:
                    state = 3
                elif state_transition & PUMP_MIN:
                    state = 5
                elif state_transition & TEMP_HIGH:
                    state = 2
                elif state_transition & TEMP_LOW:
                    state = 3
                else:
                    state = 1
            case 4:  # Max pump
                print("State 4")
                if state_transition & CRIT_TEMP:
                    state = 6
                elif not (state_transition & PUMP_MAX):
                    state = 1
                elif state_transition & TEMP_LOW:
                    state = 3
                else:
                    state = 4
            case 5:  # Minimum Pump Speed
                set_game_variable("CONDENSER_CIRCULATION_PUMP_ORDERED_SPEED", condenser_pump_min_speed)
                print("state 5")
                if state_transition & CRIT_TEMP:
                    state = 6
                elif not (state_transition & PUMP_MIN):
                    state = 1
                elif state_transition & TEMP_HIGH:
                    state = 2
                else:
                    state = 5
            case 6:  # Panic
                print("State 6")
                set_game_variable("CONDENSER_CIRCULATION_PUMP_ORDERED_SPEED", condenser_pump_max_speed)
                if not (state_transition & CRIT_TEMP):
                    state = 1
                else:
                    state = 6
            case _:
                print("State not recognized")
                state = 0
        data["condenser_controller_state"] = state
    else:
        data["condenser_controller_state"] = 100
        
        
 
 
 
 
 
 
########################################################################################################################################################
#old functions
#
#
#
#
#
#
#
#
#
#def update_secondary_loop_controllers(data):
#   #control settings
#   secondary_loop_volume_target = 24000
#   secondary_loop_slow_tolerance = 500
#   secondary_loop_high_tolerance = 2000
#   secondary_loop_high_panic = 40000
#   secondary_loop_low_panic = 15000
#   secondary_loop_min_pump = 5
#   secondary_loop_slow_update = 5
#   secondary_loop_fast_update = 0
#
#
#
#   ingame_time = data.get("TIME_STAMP") or 0
#   last_secondary_update_time = data.get("last_secondary_update_time") or 0
#   sec_last_fast_update_time = data.get("sec_last_fast_update_time",0)
#   sec_last_slow_update_time = data.get("sec_last_slow_update_time",0)
#
#   Secondary_Loop_FSM_Transition_Matrix = 
#       { "
#       #    {
#   #    "steady":
#   #        {
#   #        SEC_LOWVOL_LO | SEC_ENABLE, "increase_slow",
#   #        SEC_HIGHVOL_LO| SEC_ENABLE, "decrease_slow",
#   #        ~SEC_ENABLE & SEC_NOT_MASK, "init_off"
#   #        }
#   #    }
#
#
#   for i in range(3):
#       #get variables and setup
#       print(f"[Secondary Loop {i}] -----------------------------------------------------------------------------------------")
#       loop_state_key = f"secondary_loop{i}_controller_state"
#
#       controller_state = data.get(loop_state_key)
#       volume = data.get(f"COOLANT_SEC_{i}_VOLUME")
#       pumpspeed = data.get(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_SPEED")
#       enabled = data.get(f"secondary_pump_controller{i}_enable")
#       print(f"Controller enabled: {enabled}, Current state: {controller_state}")
#
#       #SEC_ENABLE      = 0x10000000
#       #SEC_HIGHVOL_LO  = 0x01000000
#       #SEC_HIGHVOL_HI  = 0x00100000
#       #SEC_LOWVOL_LO   = 0x00010000
#       #SEC_LOWVOL_HI   = 0x00001000
#       #SEC_MINPUMP     = 0x00000100
#       #SEC_LOWVOLPANIC = 0x00000010
#       #SEC_HIGHVOLPANIC= 0x00000001
#
#       stv = 0
#       if enabled                                                               : stv |= SEC_ENABLE
#       if None in (volume,pumpspeed)                                            : stv &= ~SEC_ENABLE
#       if volume > secondary_loop_volume_target + secondary_loop_slow_tolerance : stv |= SEC_HIGHVOL_LO
#       if volume > secondary_loop_volume_target + secondary_loop_high_tolerance : stv |= SEC_HIGHVOL_HI
#       if volume < secondary_loop_volume_target - secondary_loop_slow_tolerance : stv |= SEC_LOWVOL_LO
#       if volume > secondary_loop_volume_target - secondary_loop_high_tolerance : stv |= SEC_LOWVOL_HI
#       if volume > secondary_loop_high_panic                                    : stv |= SEC_HIGHVOLPANIC
#       if volume < secondary_loop_low_panic                                     : stv |= SEC_LOWVOLPANIC
#       if pumpspeed < secondary_loop_min_pump                                   : stv |= SEC_MINPUMP
#       
#       
#       
#
#       SECONDARY_TRANSITIONS = {
#   ("steady", SEC_LOWVOL_LO): "increase_slow",
#   ("increase_slow", SEC_LOWVOL_HI): "increase_fast",
#   ("increase_fast", 0): "increase_slow",
#   ("increase_slow", 0): "steady",
#   ("steady", SEC_HIGHVOL_LO): "decrease_slow",
#   ("decrease_slow", SEC_HIGHVOL_HI): "decrease_fast",
#   ("decrease_fast", 0): "decrease_slow",
#   ("decrease_slow", 0): "steady",
#
#
#ECONDARY_GLOBAL_OVERRIDES = [
#   (SEC_HIGHVOLPANIC, "highvol_panic"),
#   (SEC_LOWVOLPANIC, "lowvol_panic"),
#   (SEC_MINPUMP, "pump_minimum"),
#
#
#ef not_mask(variable: int, mask_to_not: int) -> int:
#   """
#   Returns the bitwise NOT of a mask, limited to the bit-width of the input variable.
#
#   Example:
#       variable      = 0b10010110 (8 bits)
#       mask_to_not   = 0b00000100
#       result        = 0b11111011
#   """
#   bit_length = variable.bit_length()
#   return (~mask_to_not) & ((1 << bit_length) - 1)
#
#
#ef FSM_Calc(Current_State, Transition_Variable, Transition_Matrix, Action_Matrix, Override_Matrix, Default_State):
#
#
#   
#   # Perform any actions specified by the Action Matrix
#   # Example:
#   #Action_Matrix =
#   #{
#   #    "increase_fast":
#   #    {
#   #        f"COOLANT_SEC_{i}_VOLUME",CurrentPumpSpeed + 5,
#   #        "SomeGameVariableName", ValueToSet
#   #    }
#   #}
#   try:
#       for var,val in Action_Matrix.get(Current_State, {}).items():
#           try:
#               set_game_variable(var,val)
#           except Exception as e:
#               print(f"[FSM_Calc] Error setting variable {var} = {val}: {e}")
#   except Exception as e:
#       print(f"[FSM_Calc] Error processing action matrix: {e}, returning current state: {Current_State}")        
#       return Current_State
#
#
#
#
#
#
#   # Override section.  This section is for transitioning to the target state, regardless of where we are.
#   #Override_Matrix = 
#   #{
#   #    SEC_ENABLE | SEC_HIGHVOLPANIC, "highvol_panic",
#   #    SEC_ENABLE | SEC_LOWVOLPANIC , "lowvol_panic",
#   #    BitMaskA   | BitMaskB        , "Target State"
#   #}
#   try:
#       for BitMask, Next_State in Override_Matrix:
#           if Transition_Variable & BitMask == BitMask:
#               return Next_State
#   except Exception as e:
#       print(f"[FSM_Calc] Error processing ovveride matrix: {e}, returning current state: {Current_State}")        
#       return Current_State
#
#   # The transition matrix. This is a matrix that describes the relationship between the states the transition variable. 
#   # It's basically a library of libraries. The outer library has the current state as the key.  The value of the outer library is an inner library.     
#   # The inner library controls what states are next from the current state and how to reach them.  The key names of the inner library contain collections of the bit masks
#   # that were used to build the state transition variable. Note that to have more than one bit mask used as the transition gate they must be OR'd together 
#   # to do a NOT logic, you must provide a mask of all 1's the same number of bits as the transition matrix and the other bit masks. This is due to
#   # pythons handling of all variables as 32 bit integers.  
#   # Note that the function loops through the matrix, so the earlier transitions in the matrix have priority.
#   #Transition_Matrix = 
#   #    {
#   #    "steady":
#   #        {
#   #        SEC_LOWVOL_LO | SEC_ENABLE, "increase_slow",
#   #        SEC_HIGHVOL_LO| SEC_ENABLE, "decrease_slow",
#   #        ~SEC_ENABLE & SEC_NOT_MASK, "init_off"
#   #        }
#   #    }
#   try:
#       for BitMask, Next_State in Transition_Matrix.get(Current_State, {}).items():
#           if Transition_Variable & BitMask == BitMask:
#               return Next_State
#   except Exception as e:
#       print(f"[FSM_Calc] Error processing transition matrix: {e}, returning current state: {Current_State}")        
#       return Current_State
#           
#                       
#   #Just in case the controller is in a state not specified in the transition matrix
#   state_transitions = Transition_Matrix.get(Current_State, {})
#   if not state_transitions:
#       print(f"[FSM_Calc] WARNING: Unknown state '{Current_State}'. Returning current state")
#       return Current_State
#       
#   print(f"[FSM_Calc] Error processing state {Current_State}. Returning current state.  Please check the matrices, you should never get this message.")
#   return Current_State
#
#ef get_secondary_next_state(current, stv):
#   if not (stv & SEC_ENABLE):
#       return "init_off"
#
#   for bit, name in SECONDARY_GLOBAL_OVERRIDES:
#       if stv & bit:
#           return name
#
#   for (from_state, condition), to_state in SECONDARY_TRANSITIONS.items():
#       if from_state == current and (stv & condition):
#           return to_state
#
#   return current
#
#
#       Steady = SEC_ENABLE
#       IncSlw = SEC_ENABLE | SEC_LOWVOL_LO
#       IncFst = SEC_ENABLE | SEC_LOWVOL_HI
#       DecSlw = SEC_ENABLE | SEC_HIGHVOL_LO
#       DecFst = SEC_ENABLE | SEC_HIGHVOL_HI
#       Panic  = SEC_HIGHVOLPANIC | SEC_LOWVOLPANIC | SEC_MINPUMP
#       MinPmp = SEC_ENABLE | SEC_MINPUMP
#       PanLow = SEC_LOWVOLPANIC
#
#       match controller_state:
#           case "init_off":
#               if stv & SEC_ENABLE : controller_state = "steady"
#               else                : controller_state = "init/off"
#
#           case "steady":
#               #No changes to pump speed
#               #controller_state = secondary_state_transition(stv)
#               if stv & Steady = Steady: controller_state = "steady"
#               if not
#
#               if (stv & SEC_ENABLE & SEC_LOWVOL_LO):
#
#               if not(stv & SEC_ENABLE)  : state = "init_off"
#               elif stv &
#
#           case "decrease_slow" :
#               if (ingame_time - sec_last_slow_update_time) > secondary_loop_slow_update:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", pumpspeed - 1)
#               controller_state = secondary_state_transition(stv)
#
#           case "decrease_fast":
#               if (ingame_time - sec_last_slow_update_time) > secondary_loop_fast_update:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", pumpspeed - 1)
#               controller_state = secondary_state_transition(stv)
#
#           case "increase_slow":
#               if (ingame_time - sec_last_slow_update_time) > secondary_loop_slow_update:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", pumpspeed + 1)
#               controller_state = secondary_state_transition(stv)
#
#           case "increase_fast":
#               if (ingame_time - sec_last_slow_update_time) > secondary_loop_fast_update:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", pumpspeed + 1)
#               controller_state = secondary_state_transition(stv)
#
#           case "pump_minimum":
#               #special state for handling an oil use feature in game.  Basically during startup 2-3%, the pump leaks oil, stupid, but it's there.
#               #The idea of this funciton is to command the pump at either 0 or minimum to minimize very slow rotations.
#               #We enter this state if the current pump speed is ever less than the minimum pump % specified.
#               #While in this state, we manage volume the volume target, turn the pump on at Low Volume for low speed setpoint, turn it off above high volume for low speed setpoint.
#               #the only way to exit this state is by going below low volume for fast update or low vol panic.
#
#               #In this state, manage the volume
#               if stv & SEC_LOWVOL_LO:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", secondary_loop_min_pump)
#               if stv & SEC_HIGHVOL_LO:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", 0)
#
#               if stv & SEC_LOWVOLPANIC:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", secondary_loop_min_pump)
#                   controller_state = "lowvol_panic"
#               elif stv & SEC_LOWVOL_HI:
#                   set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", secondary_loop_min_pump)
#                   controller_state = "increase_fast"
#               else:
#                   controller_state = "pump_minimum"
#
#           case "highvol_panic":
#               set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", 0)
#               if not(stv & SEC_ENABLE):
#                   controller_state = "init_off"
#               elif not(stv & SEC_HIGHVOLPANIC):
#                   controller_state = secondary_state_transition(stv)
#               else:
#                   controller_state = "highvol_panic"
#
#           case "lowvol_panic":
#               set_game_variable(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED", 100)
#               if not(stv & SEC_ENABLE):
#                   controller_state = "init_off"
#               elif not(stv & SEC_LOWVOLPANIC):
#                   controller_state = secondary_state_transition(stv)
#               else:
#                   controller_state = "lowvol_panic"
#
#           case _:
#               controller_state = "init_off"
#       data[loop_state_key] = controller_state