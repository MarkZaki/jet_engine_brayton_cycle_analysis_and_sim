from __future__ import annotations

from performance.thrust import compute_thrust


def shaft_efficiency(state) -> float:
    W_net = state.Wt - state.Wc
    Qin = state.Qin
    if Qin <= 0.0:
        return 0.0
    return W_net / Qin


def jet_power_efficiency(state, V0: float) -> float:
    Qin = state.Qin
    if Qin <= 0.0:
        return 0.0

    bypass_air_mass_flow = getattr(state, "bypass_air_mass_flow", 0.0)
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    specific_jet_power = 0.5 * (
        (1.0 + state.fuel_air_ratio) * state.m_dot * state.V**2
        + bypass_air_mass_flow * getattr(state, "bypass_exit_velocity", 0.0) ** 2
        - total_air_mass_flow * V0**2
    ) / max(total_air_mass_flow, 1e-9)
    return specific_jet_power / Qin


def propulsive_efficiency(state, V0: float) -> float:
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    bypass_air_mass_flow = getattr(state, "bypass_air_mass_flow", 0.0)
    jet_power = 0.5 * (
        (1.0 + state.fuel_air_ratio) * state.m_dot * state.V**2
        + bypass_air_mass_flow * getattr(state, "bypass_exit_velocity", 0.0) ** 2
        - total_air_mass_flow * V0**2
    )
    if jet_power <= 0.0:
        return 0.0

    thrust_power = compute_thrust(state, V0) * V0
    return thrust_power / jet_power


def overall_efficiency(state, V0: float) -> float:
    if state.Qin <= 0.0:
        return 0.0
    useful_power = compute_thrust(state, V0) * V0
    return useful_power / (getattr(state, "total_air_mass_flow", state.m_dot) * state.Qin)


def thermal_efficiency(state, V0: float) -> float:
    return jet_power_efficiency(state, V0)


def specific_impulse(state, V0: float, gravity: float = 9.80665) -> float:
    fuel_air_ratio = max(state.fuel_air_ratio, 0.0)
    if fuel_air_ratio <= 0.0:
        return 0.0
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    fuel_flow = total_air_mass_flow * fuel_air_ratio
    return compute_thrust(state, V0) / max(fuel_flow * gravity, 1e-9)


def tsfc(state, V0: float) -> float:
    thrust = compute_thrust(state, V0)
    if thrust <= 0.0:
        return 0.0
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    fuel_flow = total_air_mass_flow * max(state.fuel_air_ratio, 0.0)
    return fuel_flow / thrust
