from __future__ import annotations

from performance.thrust import compute_thrust


def shaft_efficiency(state) -> float:
    if state.Qin <= 0.0:
        return 0.0
    return (state.Wt - state.Wc) / state.Qin


def jet_power_efficiency(state, V0: float) -> float:
    if state.Qin <= 0.0:
        return 0.0
    jet_power = 0.5 * ((1.0 + state.fuel_air_ratio) * state.V**2 - V0**2)
    return jet_power / state.Qin


def propulsive_efficiency(state, V0: float) -> float:
    jet_power = 0.5 * ((1.0 + state.fuel_air_ratio) * state.V**2 - V0**2)
    if jet_power <= 0.0:
        return 0.0
    return compute_thrust(state, V0) * V0 / max(state.m_dot * jet_power, 1e-9)


def overall_efficiency(state, V0: float) -> float:
    if state.Qin <= 0.0:
        return 0.0
    return compute_thrust(state, V0) * V0 / max(state.m_dot * state.Qin, 1e-9)


def thermal_efficiency(state, V0: float) -> float:
    return jet_power_efficiency(state, V0)


def specific_impulse(state, V0: float, gravity: float = 9.80665) -> float:
    fuel_flow = state.m_dot * max(state.fuel_air_ratio, 0.0)
    if fuel_flow <= 0.0:
        return 0.0
    return compute_thrust(state, V0) / max(fuel_flow * gravity, 1e-9)
