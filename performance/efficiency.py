def shaft_efficiency(state):
    print("Computing efficiency with Wt:", state.Wt, "Wc:", state.Wc, "Qin:", state.Qin)
    W_net = state.Wt - state.Wc
    Qin = state.Qin

    if Qin == 0:
        return 0

    return W_net / Qin

def power_efficiency(state, V0):
    m_dot = state.m_dot
    Ve = state.V

    jet_power = 0.5 * m_dot * (Ve**2 - V0**2)

    Qin = state.Qin

    if Qin == 0:
        return 0

    return jet_power / Qin