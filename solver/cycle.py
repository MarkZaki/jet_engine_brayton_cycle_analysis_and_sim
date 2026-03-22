"""Thermodynamic helper relations used by the cycle solver."""

from __future__ import annotations

import math

from models.gas import IdealGas, STANDARD_AIR

MIN_POSITIVE = 1e-9
REFERENCE_TEMPERATURE = 288.15
REFERENCE_PRESSURE = 101325.0


def specific_volume(T: float, P: float, gas_constant: float = STANDARD_AIR.R) -> float:
    return gas_constant * T / max(P, MIN_POSITIVE)


def density(T: float, P: float, gas_constant: float = STANDARD_AIR.R) -> float:
    return P / max(gas_constant * T, MIN_POSITIVE)


def _coerce_gas(gas_or_gamma: IdealGas | float, gas_constant: float | None = None) -> IdealGas:
    if isinstance(gas_or_gamma, IdealGas):
        return gas_or_gamma

    gamma_value = float(gas_or_gamma)
    r_value = gas_constant if gas_constant is not None else STANDARD_AIR.R
    cp_value = gamma_value * r_value / max(gamma_value - 1.0, MIN_POSITIVE)
    return IdealGas(
        name=STANDARD_AIR.name,
        cp_reference=cp_value,
        gamma_reference=gamma_value,
        gas_constant=r_value,
        lower_heating_value=STANDARD_AIR.lower_heating_value,
        burner_efficiency=STANDARD_AIR.burner_efficiency,
        temperature_dependent=False,
    )


def speed_of_sound(
    T: float,
    gas_or_gamma: IdealGas | float = STANDARD_AIR,
    gas_constant: float | None = None,
) -> float:
    gas = _coerce_gas(gas_or_gamma, gas_constant)
    gamma_value = gas.gamma_at(T)
    return math.sqrt(max(MIN_POSITIVE, gamma_value * gas.R * T))


def mach_number(
    velocity: float,
    T: float,
    gas_or_gamma: IdealGas | float = STANDARD_AIR,
    gas_constant: float | None = None,
) -> float:
    return velocity / max(speed_of_sound(T, gas_or_gamma, gas_constant), MIN_POSITIVE)


def total_temperature(T: float, velocity: float, gas: IdealGas = STANDARD_AIR) -> float:
    return gas.temperature_from_enthalpy_change(T, 0.5 * velocity**2)


def static_temperature_from_total(T_total: float, velocity: float, gas: IdealGas = STANDARD_AIR) -> float:
    return max(1.0, gas.temperature_from_enthalpy_change(T_total, -0.5 * velocity**2))


def stagnation_pressure_from_static(T_static: float, P_static: float, T_total: float, gas: IdealGas = STANDARD_AIR) -> float:
    gamma_value = gas.gamma_mean(T_static, T_total)
    return P_static * (T_total / max(T_static, MIN_POSITIVE)) ** (gamma_value / (gamma_value - 1.0))


def static_pressure_from_stagnation(T_static: float, T_total: float, P_total: float, gas: IdealGas = STANDARD_AIR) -> float:
    gamma_value = gas.gamma_mean(T_static, T_total)
    return P_total * (T_static / max(T_total, MIN_POSITIVE)) ** (gamma_value / (gamma_value - 1.0))


def static_state_from_total_and_velocity(T_total: float, P_total: float, velocity: float, gas: IdealGas) -> dict[str, float]:
    T_static = static_temperature_from_total(T_total, velocity, gas)
    P_static = static_pressure_from_stagnation(T_static, T_total, P_total, gas)
    return {
        "temperature": T_static,
        "pressure": P_static,
        "density": density(T_static, P_static, gas.R),
        "specific_volume": specific_volume(T_static, P_static, gas.R),
        "mach": mach_number(velocity, T_static, gas),
    }


def stagnation_state_from_static(T_static: float, P_static: float, velocity: float, gas: IdealGas) -> dict[str, float]:
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
    cp_mean = gas.cp_mean(T1, T2)
    return cp_mean * math.log(max(T2, MIN_POSITIVE) / max(T1, MIN_POSITIVE)) - gas.R * math.log(
        max(P2, MIN_POSITIVE) / max(P1, MIN_POSITIVE)
    )


def isentropic_temperature(T_in: float, P_out: float, P_in: float, gas: IdealGas = STANDARD_AIR) -> float:
    temperature_out = T_in
    for _ in range(4):
        gamma_value = gas.gamma_mean(T_in, temperature_out)
        temperature_out = T_in * (P_out / max(P_in, MIN_POSITIVE)) ** ((gamma_value - 1.0) / gamma_value)
    return max(1.0, temperature_out)


def pressure_from_isentropic_temperature(T_in: float, T_out: float, P_in: float, gas: IdealGas = STANDARD_AIR) -> float:
    gamma_value = gas.gamma_mean(T_in, T_out)
    return P_in * (T_out / max(T_in, MIN_POSITIVE)) ** (gamma_value / (gamma_value - 1.0))


def fuel_air_ratio_for_target_temperature(
    T_out: float,
    T_in: float,
    gas: IdealGas,
    burner_efficiency: float | None = None,
) -> float:
    eta_b = burner_efficiency if burner_efficiency is not None else gas.burner_efficiency
    numerator = gas.delta_h(T_out, T_in)
    denominator = eta_b * gas.lower_heating_value - gas.cp_at(T_out) * T_out
    if denominator <= 0.0:
        return 0.0
    return max(0.0, numerator / denominator)


def critical_pressure_ratio(gamma_value: float = STANDARD_AIR.gamma_reference) -> float:
    return (2.0 / (gamma_value + 1.0)) ** (gamma_value / (gamma_value - 1.0))


def corrected_mass_flow(m_dot: float, Tt: float, Pt: float) -> float:
    return m_dot * math.sqrt(max(Tt, MIN_POSITIVE) / REFERENCE_TEMPERATURE) / max(Pt / REFERENCE_PRESSURE, MIN_POSITIVE)


def choked_area_from_total_state(T_total: float, P_total: float, gas: IdealGas, m_dot: float) -> dict[str, float]:
    if m_dot <= 0.0 or T_total <= 0.0 or P_total <= 0.0:
        return {
            "temperature": math.nan,
            "pressure": math.nan,
            "density": math.nan,
            "velocity": math.nan,
            "area": math.nan,
        }

    gamma_value = gas.gamma_at(T_total)
    T_star = T_total * 2.0 / (gamma_value + 1.0)
    P_star = P_total * critical_pressure_ratio(gamma_value)
    rho_star = density(T_star, P_star, gas.R)
    velocity_star = speed_of_sound(T_star, gas)
    throat_area = flow_area(m_dot, rho_star, velocity_star)
    return {
        "temperature": T_star,
        "pressure": P_star,
        "density": rho_star,
        "velocity": velocity_star,
        "area": throat_area,
    }


def flow_area(m_dot: float, rho: float, velocity: float) -> float:
    if m_dot <= 0.0 or rho <= 0.0 or velocity <= MIN_POSITIVE:
        return math.nan
    return m_dot / (rho * velocity)


def area_mach_ratio(M: float, gamma_value: float) -> float:
    term = (2.0 / (gamma_value + 1.0)) * (1.0 + 0.5 * (gamma_value - 1.0) * M**2)
    exponent = (gamma_value + 1.0) / (2.0 * (gamma_value - 1.0))
    return (1.0 / max(M, MIN_POSITIVE)) * term**exponent


def mach_from_area_ratio(area_ratio: float, gamma_value: float, supersonic: bool) -> float:
    lower = 1.0 + 1e-6 if supersonic else 1e-6
    upper = 12.0 if supersonic else 0.999999
    for _ in range(80):
        midpoint = 0.5 * (lower + upper)
        value = area_mach_ratio(midpoint, gamma_value)
        if supersonic:
            if value > area_ratio:
                lower = midpoint
            else:
                upper = midpoint
        else:
            if value > area_ratio:
                lower = midpoint
            else:
                upper = midpoint
    return 0.5 * (lower + upper)


def nozzle_exit_state(
    T_total: float,
    P_total: float,
    ambient_pressure: float,
    gas: IdealGas,
    eta_n: float,
    m_dot: float,
    nozzle_type: str = "convergent",
    throat_area: float | None = None,
    exit_area: float | None = None,
    total_pressure_loss: float = 0.0,
) -> dict[str, float | bool | str]:
    P_total_available = P_total * (1.0 - total_pressure_loss)
    if T_total <= 0.0 or P_total_available <= 0.0 or ambient_pressure <= 0.0 or m_dot <= 0.0:
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
            "continuity_error": math.nan,
            "message": "Nozzle inlet conditions were invalid for a physical solution.",
        }

    gamma_value = gas.gamma_at(T_total)
    critical_ratio = critical_pressure_ratio(gamma_value)
    critical_pressure = P_total_available * critical_ratio
    choked = ambient_pressure <= critical_pressure
    throat = choked_area_from_total_state(T_total, P_total_available, gas, m_dot)
    required_throat_area = throat["area"]
    available_throat_area = throat_area if throat_area is not None else required_throat_area

    if throat_area is not None and required_throat_area > throat_area * 1.0001:
        return {
            "temperature": math.nan,
            "pressure": math.nan,
            "velocity": 0.0,
            "density": math.nan,
            "mach": math.nan,
            "exit_area": exit_area if exit_area is not None else math.nan,
            "throat_area": throat_area,
            "pressure_thrust": 0.0,
            "choked": choked,
            "feasible": False,
            "continuity_error": math.nan,
            "message": "Specified nozzle throat area is smaller than the throat area required to pass the requested mass flow.",
        }

    supersonic_capable = nozzle_type == "converging-diverging" and choked and exit_area is not None and exit_area > available_throat_area
    if supersonic_capable:
        area_ratio = exit_area / max(available_throat_area, MIN_POSITIVE)
        exit_mach_isentropic = mach_from_area_ratio(area_ratio, gamma_value, supersonic=True)
        exit_temperature_isentropic = T_total / (1.0 + 0.5 * (gamma_value - 1.0) * exit_mach_isentropic**2)
        exit_pressure_isentropic = P_total_available * (
            exit_temperature_isentropic / max(T_total, MIN_POSITIVE)
        ) ** (gamma_value / (gamma_value - 1.0))
        exit_pressure = exit_pressure_isentropic
        ideal_enthalpy_drop = max(0.0, gas.delta_h(T_total, exit_temperature_isentropic))
        actual_enthalpy_drop = eta_n * ideal_enthalpy_drop
        exit_temperature = gas.temperature_from_enthalpy_change(T_total, -actual_enthalpy_drop)
        exit_velocity = math.sqrt(max(0.0, 2.0 * actual_enthalpy_drop))
        rho_exit = density(exit_temperature, exit_pressure, gas.R)
        required_exit_area = flow_area(m_dot, rho_exit, exit_velocity)
        continuity_error = (required_exit_area - exit_area) / max(exit_area, MIN_POSITIVE)
        feasible = math.isfinite(required_exit_area) and abs(continuity_error) < 0.15
        pressure_thrust = (exit_pressure - ambient_pressure) * exit_area if feasible else 0.0
        return {
            "temperature": exit_temperature,
            "pressure": exit_pressure,
            "velocity": exit_velocity,
            "density": rho_exit,
            "mach": mach_number(exit_velocity, exit_temperature, gas),
            "exit_area": exit_area,
            "throat_area": available_throat_area,
            "pressure_thrust": pressure_thrust,
            "choked": choked,
            "feasible": feasible,
            "continuity_error": continuity_error,
            "message": "" if feasible else "Fixed exit area is inconsistent with the requested mass flow for the chosen nozzle geometry.",
        }

    exit_pressure = critical_pressure if choked else ambient_pressure
    exit_temperature_isentropic = isentropic_temperature(T_total, exit_pressure, P_total_available, gas)
    ideal_enthalpy_drop = max(0.0, gas.delta_h(T_total, exit_temperature_isentropic))
    actual_enthalpy_drop = eta_n * ideal_enthalpy_drop
    exit_temperature = gas.temperature_from_enthalpy_change(T_total, -actual_enthalpy_drop)
    exit_velocity = math.sqrt(max(0.0, 2.0 * actual_enthalpy_drop))
    rho_exit = density(exit_temperature, exit_pressure, gas.R)
    required_exit_area = flow_area(m_dot, rho_exit, exit_velocity)
    final_exit_area = exit_area if exit_area is not None else required_exit_area
    feasible = math.isfinite(required_exit_area)
    continuity_error = 0.0

    if exit_area is not None:
        continuity_error = (required_exit_area - exit_area) / max(exit_area, MIN_POSITIVE)
        feasible = feasible and abs(continuity_error) < 0.15

    if not feasible:
        return {
            "temperature": exit_temperature,
            "pressure": exit_pressure,
            "velocity": exit_velocity,
            "density": rho_exit,
            "mach": mach_number(exit_velocity, exit_temperature, gas),
            "exit_area": final_exit_area,
            "throat_area": available_throat_area,
            "pressure_thrust": 0.0,
            "choked": choked,
            "feasible": False,
            "continuity_error": continuity_error,
            "message": "The nozzle could not satisfy continuity with the requested mass flow and geometry.",
        }

    pressure_thrust = (exit_pressure - ambient_pressure) * final_exit_area
    return {
        "temperature": exit_temperature,
        "pressure": exit_pressure,
        "velocity": exit_velocity,
        "density": rho_exit,
        "mach": mach_number(exit_velocity, exit_temperature, gas),
        "exit_area": final_exit_area,
        "throat_area": available_throat_area,
        "pressure_thrust": pressure_thrust,
        "choked": choked,
        "feasible": True,
        "continuity_error": continuity_error,
        "message": "",
    }
