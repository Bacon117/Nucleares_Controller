
from typing import Tuple

def fsm_bitmask_generator(*conditions: Tuple[int, int]) -> Tuple[int, int]:
    """
    Builds a tuple (expected_bits, check_mask) for FSM comparison.
    Each condition is (bitmask, state), where:
        ON  → must be 1
        OFF → must be 0
        ANY → don't care (ignored)

    Returns:
        expected: bitmask with required ON bits
        mask:     bitmask with bits that must be tested (ON or OFF)
    """
    expected = 0
    mask = 0
    for bit, state in conditions:
        if state == 2:
            continue
        mask |= bit
        if state == 1:
            expected |= bit
    return expected, mask