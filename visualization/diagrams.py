def PV_diagram(states):
    """Generate data for a P-V diagram."""
    return [(state.V, state.P) for state in states]

def TS_diagram(states):
    """Generate data for a T-S diagram."""
    return [(state.s, state.T) for state in states]

def TP_diagram(states):
    """Generate data for a T-P diagram."""
    return [(state.P, state.T) for state in states]

def performance_diagram(states):
    """Generate data for performance metrics."""
    return [(state.stage_name, state.Wc, state.Wt) for state in states]