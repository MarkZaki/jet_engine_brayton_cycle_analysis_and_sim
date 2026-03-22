from performance.thrust import compute_thrust


def shaft_efficiency(state):
    W_net = state.Wt - state.Wc
    Qin = state.Qin

    if Qin <= 0:
        return 0.0

    return W_net / Qin


def jet_power_efficiency(state, V0):
    Qin = state.Qin
    if Qin <= 0:
        return 0.0

    specific_jet_power = 0.5 * ((1.0 + state.fuel_air_ratio) * state.V**2 - V0**2)
    return specific_jet_power / Qin


def propulsive_efficiency(state, V0):
    specific_jet_power = 0.5 * ((1.0 + state.fuel_air_ratio) * state.V**2 - V0**2)
    if specific_jet_power <= 0:
        return 0.0

    thrust_power = compute_thrust(state, V0) * V0
    jet_power = state.m_dot * specific_jet_power
    if jet_power <= 0:
        return 0.0

    return thrust_power / jet_power


def overall_efficiency(state, V0):
    Qin = state.Qin
    if Qin <= 0:
        return 0.0

    useful_power = compute_thrust(state, V0) * V0
    return useful_power / (state.m_dot * Qin)


def power_efficiency(state, V0):
    return jet_power_efficiency(state, V0)
