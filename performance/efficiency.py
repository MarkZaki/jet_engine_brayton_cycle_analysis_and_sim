def shaft_efficiency(state):
    W_net = state.Wt - state.Wc
    Qin = state.Qin

    if Qin <= 0:
        return 0

    return W_net / Qin

def power_efficiency(state, V0):
    Ve = state.V

    Qin = state.Qin

    if Qin <= 0:
        return 0

    specific_jet_power = 0.5 * (Ve**2 - V0**2)
    return specific_jet_power / Qin
