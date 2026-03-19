def compute_thrust(state, V0):
    m_dot_air = state.m_dot
    m_dot_exit = m_dot_air * (1.0 + state.fuel_air_ratio)
    momentum_thrust = m_dot_exit * state.V - m_dot_air * V0
    return momentum_thrust + state.pressure_thrust
