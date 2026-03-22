def compute_thrust(subject, V0):
    state = subject.final_state if hasattr(subject, "final_state") else subject
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    bypass_air_mass_flow = getattr(state, "bypass_air_mass_flow", 0.0)
    bypass_exit_velocity = getattr(state, "bypass_exit_velocity", 0.0)
    bypass_pressure_thrust = getattr(state, "bypass_pressure_thrust", 0.0)
    m_dot_core_exit = state.m_dot * (1.0 + state.fuel_air_ratio)
    momentum_thrust = m_dot_core_exit * state.V + bypass_air_mass_flow * bypass_exit_velocity - total_air_mass_flow * V0
    return momentum_thrust + state.pressure_thrust + bypass_pressure_thrust
