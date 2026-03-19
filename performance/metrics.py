def compute_bwr(state):
    if state.Wt == 0:
        return 0
    return state.Wc / state.Wt

def specific_work(state):
    return state.Wt - state.Wc