def compute_thrust(state, V0):
    return state.m_dot * (state.V - V0)