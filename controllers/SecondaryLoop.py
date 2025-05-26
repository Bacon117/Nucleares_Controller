
from typing import Any, Dict

from controllers.Utilities.helper_func import fsm_bitmask_generator
from controllers.Utilities.FSM_Calc import FSM_Calc


#global variable defs
SEC_ENABLE      = 0b1000000
SEC_HIGHVOL_LO  = 0b0100000
SEC_HIGHVOL_HI  = 0b0010000
SEC_LOWVOL_LO   = 0b0001000
SEC_LOWVOL_HI   = 0b0000100
SEC_PANIC       = 0b0000010
SEC_PANIC_EXIT  = 0b0000001



PANIC_ENABLE        = 0b10000
PANIC_MINPUMP_LOVOL = 0b01000
PANIC_MINPUMP_HIVOL = 0b00100
PANIC_LO_VOLUME     = 0b00010
PANIC_HI_VOLUME     = 0b00001



 
def update_secondary_loop_controllers(data:Dict[Any,Any]):
    
    #--------------------------------------------------------Control Settings ----------------------------------------------------
    secondary_loop_volume_target  = data.setdefault("secondary_loop_volume_target" ,24000)      
    secondary_loop_slow_tolerance = data.setdefault("secondary_loop_slow_tolerance",500  )    
    secondary_loop_high_tolerance = data.setdefault("secondary_loop_high_tolerance",2000 )     
    secondary_loop_high_panic     = data.setdefault("secondary_loop_high_panic"    ,40000)      
    secondary_loop_low_panic      = data.setdefault("secondary_loop_low_panic"     ,15000)      
    secondary_loop_pump_min       = data.setdefault("secondary_loop_pump_min"      ,5    )  
    secondary_loop_pump_max       = data.setdefault("secondary_loop_pump_max"      ,100  )  
    secondary_loop_pump_off       = data.setdefault("secondary_loop_pump_off"      ,0  )  
    secondary_loop_slow_update    = data.setdefault("secondary_loop_slow_update"   ,3    )  
    secondary_loop_fast_update    = data.setdefault("secondary_loop_fast_update"   ,1    )    
  



    #set up transition bit masks for the outer state machine    
    #True, False, either = 1, 0, 2
    to_steady  = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 0), (SEC_HIGHVOL_HI, 0), (SEC_LOWVOL_LO, 0), (SEC_LOWVOL_HI, 0), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 2))
    to_dec_slo = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 1), (SEC_HIGHVOL_HI, 2), (SEC_LOWVOL_LO, 0), (SEC_LOWVOL_HI, 0), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 2))
    to_dec_fst = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 2), (SEC_HIGHVOL_HI, 1), (SEC_LOWVOL_LO, 0), (SEC_LOWVOL_HI, 0), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 2))
    to_inc_slo = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 0), (SEC_HIGHVOL_HI, 0), (SEC_LOWVOL_LO, 1), (SEC_LOWVOL_HI, 2), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 2))
    to_inc_fst = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 0), (SEC_HIGHVOL_HI, 0), (SEC_LOWVOL_LO, 2), (SEC_LOWVOL_HI, 1), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 2))
    to_panic   = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 2), (SEC_HIGHVOL_HI, 2), (SEC_LOWVOL_LO, 2), (SEC_LOWVOL_HI, 2), (SEC_PANIC, 1), (SEC_PANIC_EXIT, 2))
    fr_panic   = fsm_bitmask_generator((SEC_ENABLE, 2), (SEC_HIGHVOL_LO, 2), (SEC_HIGHVOL_HI, 2), (SEC_LOWVOL_LO, 2), (SEC_LOWVOL_HI, 2), (SEC_PANIC, 0), (SEC_PANIC_EXIT, 1))
    #create the FSM transition matrix
    Secondary_Loop_FSM_Transition_Matrix = { 
        "off_init" : {
            to_steady : "steady"
        },
        
        "steady" : {
            to_panic   : "panic",
            to_dec_slo : "decrease_slow",
            to_inc_slo : "increase_slow",
            to_steady  : "steady"
        },
        
        "increase_slow": {
            to_panic   : "panic",
            to_inc_fst : "increase_fast",
            to_steady  : "steady",
            to_inc_slo : "increase_slow"
        },
        "increase_fast": {
            to_panic   : "panic",
            to_inc_slo : "increase_slow",
            to_inc_fst : "increase_fast"
        },
        "decrease_slow": {
            to_panic   : "panic",
            to_dec_fst : "decrease_fast",
            to_dec_slo : "decrease_slow",
            to_steady  : "steady"
        },
        "decrease_fast": {
            to_panic   : "panic",
            to_dec_fst : "decrease_fast",
            to_dec_slo : "decrease_slow",                             
        },
        "panic": {
            fr_panic : "steady"
        }
    } 


  
    #set up the transition bit masks for the panic handler
    # 0 bit mask in NOT, 
    
    p_to_lovol   = fsm_bitmask_generator((PANIC_ENABLE,1),(PANIC_MINPUMP_LOVOL,0),(PANIC_MINPUMP_HIVOL,0),(PANIC_LO_VOLUME,1),(PANIC_HI_VOLUME,0))
    p_to_hivol   = fsm_bitmask_generator((PANIC_ENABLE,1),(PANIC_MINPUMP_LOVOL,0),(PANIC_MINPUMP_HIVOL,0),(PANIC_LO_VOLUME,0),(PANIC_HI_VOLUME,1))
    p_to_pumpoff = fsm_bitmask_generator((PANIC_ENABLE,1),(PANIC_MINPUMP_LOVOL,0),(PANIC_MINPUMP_HIVOL,1),(PANIC_LO_VOLUME,0),(PANIC_HI_VOLUME,0))
    p_to_pumpmin = fsm_bitmask_generator((PANIC_ENABLE,1),(PANIC_MINPUMP_LOVOL,1),(PANIC_MINPUMP_HIVOL,0),(PANIC_LO_VOLUME,0),(PANIC_HI_VOLUME,0))
    p_fr_lovol   = fsm_bitmask_generator((PANIC_ENABLE,2),(PANIC_MINPUMP_LOVOL,0),(PANIC_MINPUMP_HIVOL,2),(PANIC_LO_VOLUME,2),(PANIC_HI_VOLUME,2))
    p_fr_hivol   = fsm_bitmask_generator((PANIC_ENABLE,2),(PANIC_MINPUMP_LOVOL,1),(PANIC_MINPUMP_HIVOL,2),(PANIC_LO_VOLUME,2),(PANIC_HI_VOLUME,2))
    p_fr_pumpmin = fsm_bitmask_generator((PANIC_ENABLE,2),(PANIC_MINPUMP_LOVOL,2),(PANIC_MINPUMP_HIVOL,2),(PANIC_LO_VOLUME,2),(PANIC_HI_VOLUME,1))

    #create the panic mode transition matrix
    Panic_Mode_FSM_Transition_Matrix = {
        "init": {
            p_to_lovol  : "LoVolume",
            p_to_hivol  : "HiVolume",
            p_to_pumpmin: "PumpMin",
            p_to_pumpoff: "PumpOff"

        },
        "LoVolume": {
            p_to_lovol  : "LoVolume",
            p_fr_lovol  : "Exit"
        },
        "HiVolume": {
            p_to_hivol  : "HiVolume",
            p_fr_hivol  : "Exit"
        },
        "PumpMin": {
            p_to_pumpmin: "PumpMin",
            p_to_pumpoff: "PumpOff",
            p_fr_pumpmin: "Exit"
        },
        "PumpOff": {
            p_to_pumpmin: "PumpMin",
            p_to_pumpoff: "PumpOff"

        }
    }

    for i in range(3):
        #get variables and setup
        print(f"[Secondary Loop {i}] -----------------------------------------------------------------------------------------")
        loop_state_key = f"secondary_loop{i}_controller_state"        
        secondary_controller_state = data.get(loop_state_key,"off_init")
        secondary_panic_state      = data.get(loop_state_key + "_panic","Exit")
        volume = data.get(f"COOLANT_SEC_{i}_VOLUME")
        pumpspeed = data.get(f"COOLANT_SEC_CIRCULATION_PUMP_{i}_SPEED")
        enabled = data.get(f"secondary_pump_controller{i}_enable")
        print(f"Controller enabled: {enabled}, Current state: {secondary_controller_state}")
        
        
        
        
        panic =any([
            volume > secondary_loop_high_panic,
            volume < secondary_loop_low_panic,
            pumpspeed <= secondary_loop_pump_min
        ])
        if panic and secondary_panic_state == "Exit":secondary_panic_state = "init"

        state_transition_variable = 0
        if enabled                                                               : state_transition_variable |= SEC_ENABLE
        if None in (volume,pumpspeed)                                            : state_transition_variable &= ~SEC_ENABLE
        if volume > secondary_loop_volume_target + secondary_loop_slow_tolerance : state_transition_variable |= SEC_HIGHVOL_LO
        if volume > secondary_loop_volume_target + secondary_loop_high_tolerance : state_transition_variable |= SEC_HIGHVOL_HI
        if volume < secondary_loop_volume_target - secondary_loop_slow_tolerance : state_transition_variable |= SEC_LOWVOL_LO
        if volume > secondary_loop_volume_target - secondary_loop_high_tolerance : state_transition_variable |= SEC_LOWVOL_HI
        if panic                                                                 : state_transition_variable |= SEC_PANIC
        if secondary_panic_state == "exit"                                       : state_transition_variable |= SEC_PANIC_EXIT       
        
        state_transition_variable_panic = 0
        if panic                                                                 : state_transition_variable_panic |= PANIC_ENABLE
        if volume < secondary_loop_volume_target - secondary_loop_high_tolerance : state_transition_variable_panic |= PANIC_MINPUMP_LOVOL
        if volume > secondary_loop_volume_target + secondary_loop_high_tolerance : state_transition_variable_panic |= PANIC_MINPUMP_HIVOL
        if volume < secondary_loop_low_panic                                     : state_transition_variable_panic |= PANIC_LO_VOLUME
        if volume > secondary_loop_high_panic                                    : state_transition_variable_panic |= PANIC_HI_VOLUME




        secondary_action_matrix = {
            "increase_slow":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":pumpspeed + secondary_loop_slow_update},
            "increase_fast":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":pumpspeed + secondary_loop_fast_update},
            "decrease_slow":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":pumpspeed - secondary_loop_slow_update},
            "decrease_fast":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":pumpspeed - secondary_loop_fast_update},
        }

        secondary_action_matrix_panic = {
            "LoVolume":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":secondary_loop_pump_max},
            "HiVolume":{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":secondary_loop_pump_off},
            "PumpMin" :{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":secondary_loop_pump_min},
            "PumpOff" :{f"COOLANT_SEC_CIRCULATION_PUMP_{i}_ORDERED_SPEED":secondary_loop_pump_off}
        }

        secondary_global_override_matrix = [
            (fsm_bitmask_generator((SEC_ENABLE,0)),"off_init")
        ]

        secondary_global_override_matrix_panic = [
            (fsm_bitmask_generator((PANIC_ENABLE,0)),"Exit")
        ]

        secondary_controller_state = FSM_Calc(
            secondary_controller_state,
            state_transition_variable,
            Secondary_Loop_FSM_Transition_Matrix,
            secondary_action_matrix,
            secondary_global_override_matrix
        )

        secondary_panic_state = FSM_Calc(
            secondary_panic_state,
            state_transition_variable_panic,
            Panic_Mode_FSM_Transition_Matrix,
            secondary_action_matrix_panic,
            secondary_global_override_matrix_panic
        )
        data[loop_state_key] = secondary_controller_state
        data[loop_state_key + "_panic"] = secondary_panic_state

































































