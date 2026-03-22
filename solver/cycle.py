"""Constant-property thermodynamic helper relations for a simple Brayton cycle."""

from __future__ import annotations

import math

from models.gas import IdealGas, STANDARD_AIR

MIN_POSITIVE = 1e-9


def specific_volume(T: float, P: float, gas_constant: float = STANDARD_AIR.R) -> float:
    return gas_constant * T / max(P, MIN_POSITIVE)


def density(T: float, P: float, gas_constant: float = STANDARD_AIR.R) -> float:
    return P / max(gas_constant * T, MIN_POSITIVE)


def speed_of_sound(T: float, gas: IdealGas = STANDARD_AIR) -> float:
    return math.sqrt(max(MIN_POSITIVE, gas.gamma * gas.R * T))


def mach_number(velocity: float, T: float, gas: IdealGas = STANDARD_AIR) -> float:
    return velocity / max(speed_of_sound(T, gas), MIN_POSITIVE)


def total_temperature(T: float, velocity: float, gas: IdealGas = STANDARD_AIR) -> float:
    return T + velocity**2 / (2.0 * gas.cp)


def static_temperature_from_total(T_total: float, velocity: float, gas: IdealGas = STANDARD_AIR) -> float:
    return max(1.0, T_total - velocity**2 / (2.0 * gas.cp))


def stagnation_pressure_from_static(
    T_static: float,
    P_static: float,
    T_total: float,
    gas: IdealGas = STANDARD_AIR,
) -> float:
    exponent = gas.gamma / (gas.gamma - 1.0)
    return P_static * (T_total / max(T_static, MIN_POSITIVE)) ** exponent


def static_pressure_from_stagnation(
    T_static: float,
    T_total: float,
    P_total: float,
    gas: IdealGas = STANDARD_AIR,
) -> float:
    exponent = gas.gamma / (gas.gamma - 1.0)
    return P_total * (T_static / max(T_total, MIN_POSITIVE)) ** exponent


def static_state_from_total_and_velocity(
    T_total: float,
    P_total: float,
    velocity: float,
    gas: IdealGas,
) -> dict[str, float]:
    T_static = static_temperature_from_total(T_total, velocity, gas)
    P_static = static_pressure_from_stagnation(T_static, T_total, P_total, gas)
    return {
        "temperature": T_static,
        "pressure": P_static,
        "density": density(T_static, P_static, gas.R),
        "specific_volume": specific_volume(T_static, P_static, gas.R),
        "mach": mach_number(velocity, T_static, gas),
    }


def stagnation_state_from_static(
    T_static: float,
    P_static: float,
    velocity: float,
    gas: IdealGas,
) -> dict[str, float]:
    T_total = total_temperature(T_static, velocity, gas)
    P_total = stagnation_pressure_from_static(T_static, P_static, T_total, gas)
    return {
        "temperature": T_total,
        "pressure": P_total,
        "mach": mach_number(velocity, T_static, gas),
    }


def entropy_change(
    T2: float,
    T1: float,
    P2: float,
    P1: float,
    gas: IdealGas = STANDARD_AIR,
) -> float:
    return gas.cp * math.log(max(T2, MIN_POSITIVE) / max(T1, MIN_POSITIVE)) - gas.R * math.log(
        max(P2, MIN_POSITIVE) / max(P1, MIN_POSITIVE)
    )


def isentropic_temperature(
    T_in: float,
    P_out: float,
    P_in: float,
    gas: IdealGas = STANDARD_AIR,
) -> float:
    exponent = (gas.gamma - 1.0) / gas.gamma
    return max(1.0, T_in * (P_out / max(P_in, MIN_POSITIVE)) ** exponent)


def critical_pressure_ratio(gas: IdealGas = STANDARD_AIR) -> float:
    gamma_value = gas.gamma
    return (2.0 / (gamma_value + 1.0)) ** (gamma_value / (gamma_value - 1.0))


def flow_area(m_dot: float, rho: float, velocity: float) -> float:
    if m_dot <= 0.0 or rho <= 0.0 or velocity <= MIN_POSITIVE:
        return math.nan
    return m_dot / (rho * velocity)


def nozzle_exit_state(
    T_total: float,
    P_total: float,
    ambient_pressure: float,
    gas: IdealGas,
    eta_n: float,
    m_dot: float,
) -> dict[str, float | bool | str]:
    if T_total <= 0.0 or P_total <= 0.0 or ambient_pressure <= 0.0 or m_dot <= 0.0:
        return {
            "temperature": math.nan,
            "pressure": math.nan,
            "velocity": 0.0,
            "density": math.nan,
            "mach": math.nan,
            "exit_area": math.nan,
            "throat_area": math.nan,
            "pressure_thrust": 0.0,
            "choked": False,
            "feasible": False,
            "message": "Nozzle inlet conditions are not physical.",
        }

    critical_pressure = P_total * critical_pressure_ratio(gas)
    choked = ambient_pressure <= critical_pressure
    exit_pressure = critical_pressure if choked else ambient_pressure

    T_exit_isentropic = isentropic_temperature(T_total, exit_pressure, P_total, gas)
    T_exit = T_total - eta_n * (T_total - T_exit_isentropic)
    T_exit = max(1.0, min(T_exit, T_total))
    exit_velocity = math.sqrt(max(0.0, 2.0 * gas.cp * (T_total - T_exit)))
    exit_density = density(T_exit, exit_pressure, gas.R)
    exit_area = flow_area(m_dot, exit_density, exit_velocity)

    T_star = 2.0 * T_total / (gas.gamma + 1.0)
    P_star = critical_pressure
    rho_star = density(T_star, P_star, gas.R)
    a_star = speed_of_sound(T_star, gas)
    throat_area = flow_area(m_dot, rho_star, a_star) if choked else exit_area

    feasible = math.isfinite(exit_area) and exit_velocity > 0.0
    return {
        "temperature": T_exit,
        "pressure": exit_pressure,
        "velocity": exit_velocity,
        "density": exit_density,
        "mach": mach_number(exit_velocity, T_exit, gas),
        "exit_area": exit_area,
        "throat_area": throat_area,
        "pressure_thrust": (exit_pressure - ambient_pressure) * exit_area if feasible else 0.0,
        "choked": choked,
        "feasible": feasible,
        "message": "" if feasible else "Nozzle expansion produced a non-physical exit condition.",
    }
