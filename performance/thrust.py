def compute_thrust(subject, V0):
    state = subject.final_state if hasattr(subject, "final_state") else subject
    m_dot_exit = state.m_dot * (1.0 + state.fuel_air_ratio)
    momentum_thrust = m_dot_exit * state.V - state.m_dot * V0
    return momentum_thrust + state.pressure_thrust
