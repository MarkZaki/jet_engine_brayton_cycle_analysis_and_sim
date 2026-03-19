import math

import numpy as np

CLOSING_STAGE_NAME = "Heat Rejection"
POINTS_PER_PROCESS = 40


def _coerce_states(result_or_states):
    return result_or_states.states if hasattr(result_or_states, "states") else result_or_states


def _station_values(state, ideal=False):
    if ideal:
        return {
            "label": state.stage_name or "Freestream",
            "T": state.T_ideal,
            "P": state.P_ideal,
            "s": state.s_ideal,
            "v": state.v_ideal,
            "cp": state.cp,
            "R": state.R,
        }

    return {
        "label": state.stage_name or "Freestream",
        "T": state.T,
        "P": state.P,
        "s": state.s,
        "v": state.v,
        "cp": state.cp,
        "R": state.R,
    }


def _sample_linear(start, end):
    temperatures = np.linspace(start["T"], end["T"], POINTS_PER_PROCESS)
    pressures = np.linspace(start["P"], end["P"], POINTS_PER_PROCESS)
    specific_volumes = start["R"] * temperatures / pressures
    entropies = (
        start["s"]
        + start["cp"] * np.log(temperatures / start["T"])
        - start["R"] * np.log(pressures / start["P"])
    )
    return list(zip(specific_volumes, pressures, entropies, temperatures))


def _sample_polytropic(start, end):
    if math.isclose(start["v"], end["v"]) or math.isclose(start["P"], end["P"]):
        return _sample_linear(start, end)

    exponent = math.log(end["P"] / start["P"]) / math.log(start["v"] / end["v"])
    specific_volumes = np.linspace(start["v"], end["v"], POINTS_PER_PROCESS)
    pressures = start["P"] * (start["v"] / specific_volumes) ** exponent
    temperatures = pressures * specific_volumes / start["R"]
    entropies = (
        start["s"]
        + start["cp"] * np.log(temperatures / start["T"])
        - start["R"] * np.log(pressures / start["P"])
    )
    return list(zip(specific_volumes, pressures, entropies, temperatures))


def _sample_process(stage_name, start, end):
    if stage_name in {"Combustor", CLOSING_STAGE_NAME}:
        return _sample_linear(start, end)

    return _sample_polytropic(start, end)


def _build_path(states, ideal=False, close_cycle=False):
    stations = [_station_values(state, ideal) for state in states]
    curve = []

    for index in range(1, len(states)):
        stage_name = states[index].stage_name or f"Stage {index}"
        start = stations[index - 1]
        end = stations[index]
        segment = _sample_process(stage_name, start, end)
        if curve:
            segment = segment[1:]
        curve.extend(segment)

    if close_cycle and len(stations) > 1:
        segment = _sample_process(CLOSING_STAGE_NAME, stations[-1], stations[0])[1:]
        curve.extend(segment)

    return {"curve": curve, "stations": stations}


def PV_diagram(result_or_states):
    states = _coerce_states(result_or_states)
    return {
        "actual": _build_path(states, ideal=False, close_cycle=False),
        "ideal": _build_path(states, ideal=True, close_cycle=True),
    }


def TS_diagram(result_or_states):
    states = _coerce_states(result_or_states)
    return {
        "actual": _build_path(states, ideal=False, close_cycle=False),
        "ideal": _build_path(states, ideal=True, close_cycle=True),
    }


def TP_diagram(result_or_states):
    states = _coerce_states(result_or_states)
    return {
        "actual": _build_path(states, ideal=False, close_cycle=False),
        "ideal": _build_path(states, ideal=True, close_cycle=True),
    }


def performance_diagram(result_or_states):
    states = _coerce_states(result_or_states)
    return {
        "stage_names": [state.stage_name or "Freestream" for state in states],
        "actual_net": [state.Wt - state.Wc for state in states],
        "ideal_net": [state.Wt_ideal - state.Wc_ideal for state in states],
        "actual_heat": [state.Qin for state in states],
        "ideal_heat": [state.Qin_ideal for state in states],
    }
