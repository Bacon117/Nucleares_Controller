from typing import Any, Dict, List, Tuple

from sim_api import set_game_variable



def FSM_Calc(
    Current_State: Any,
    Transition_Variable: int,
    Transition_Matrix: Dict[Any, Dict[Any, Any]],
    Action_Matrix: Dict[Any, Dict[str, Any]],
    Override_Matrix: List[Tuple[Any, Any]]
    ) -> Any:

    """
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                 ACTION MATRIX
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
    
     Perform any actions specified by the Action Matrix
     Example:
    Action_Matrix =
    {
        "increase_fast":
        {
            f"COOLANT_SEC_{i}_VOLUME",CurrentPumpSpeed + 5,
            "SomeGameVariableName", ValueToSet
        }
    }
    """    
    try:
        for var,val in Action_Matrix.get(Current_State, {}).items():
            try:
                set_game_variable(var,val)
            except Exception as e:
                print(f"[FSM_Calc] Error setting variable {var} = {val}: {e}")
    except Exception as e:
        print(f"[FSM_Calc] Error processing action matrix: {e}, returning current state: {Current_State}")        
        return Current_State


    """
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                 OVERRIDE MATRIX
    -------------------------------------------------------------------------------------------------------------------------------------------------------------



    Override section.  This section is for transitioning to the target state, regardless of where we are.
    Override_Matrix = 
    {
        SEC_ENABLE | SEC_HIGHVOLPANIC, "highvol_panic",
        SEC_ENABLE | SEC_LOWVOLPANIC , "lowvol_panic",
        BitMaskA   | BitMaskB        , "Target State"
    }
    """
    try:
        for BitMask, Next_State in Override_Matrix:
            if Transition_Variable & BitMask == BitMask:
                return Next_State
    except Exception as e:
        print(f"[FSM_Calc] Error processing overide matrix: {e}, returning current state: {Current_State}")        
        return Current_State


    """
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                 TRANSITION MATRIX
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    
    
     The transition matrix. This is a matrix that describes the relationship between the states the transition variable. 
     It's basically a library of libraries. The outer library has the current state as the key.  The value of the outer library is an inner library.     
     The inner library controls what states are next from the current state and how to reach them.  The key names of the inner library contain collections of the bit masks
     that were used to build the state transition variable. Note that to have more than one bit mask used as the transition gate they must be OR'd together 
     to do a NOT logic, you must provide a mask of all 1's the same number of bits as the transition matrix and the other bit masks. This is due to
     pythons handling of all variables as 32 bit integers.  
     Note that the function loops through the matrix, so the earlier transitions in the matrix have priority.
    Transition_Matrix = 
        {
        "steady":
            {
            SEC_LOWVOL_LO | SEC_ENABLE, "increase_slow",
            SEC_HIGHVOL_LO| SEC_ENABLE, "decrease_slow",
            ~SEC_ENABLE & SEC_NOT_MASK, "init_off"
            }
        }
    """
    try:
        for BitMask, Next_State in Transition_Matrix.get(Current_State, {}).items():
            if Transition_Variable & BitMask == BitMask:
                return Next_State
    except Exception as e:
        print(f"[FSM_Calc] Error processing transition matrix: {e}, returning current state: {Current_State}")        
        return Current_State
            
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    #                                                             FAULT HANDLING
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Just in case the controller is in a state not specified in the transition matrix
    state_transitions = Transition_Matrix.get(Current_State, {})
    if not state_transitions:
        print(f"[FSM_Calc] WARNING: Unknown state '{Current_State}'. Returning current state")
        return Current_State
        
    
    return Current_State