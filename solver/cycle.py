"""Thermodynamic helper relations used by the cycle solver."""

import math

from models.gas import STANDARD_AIR


def specific_volume(T, P, gas_constant=STANDARD_AIR.R):
    return gas_constant * T / P


def total_temperature(T, velocity, cp=STANDARD_AIR.cp):
    return T + velocity**2 / (2.0 * cp)


def static_temperature_from_total(T_total, velocity, cp=STANDARD_AIR.cp):
    return T_total - velocity**2 / (2.0 * cp)


def stagnation_pressure_from_static(T_static, P_static, T_total, gamma_value=STANDARD_AIR.gamma):
    return P_static * (T_total / T_static) ** (gamma_value / (gamma_value - 1.0))


def static_pressure_from_stagnation(T_static, T_total, P_total, gamma_value=STANDARD_AIR.gamma):
    return P_total * (T_static / T_total) ** (gamma_value / (gamma_value - 1.0))


def entropy_change(T2, T1, P2, P1, cp=STANDARD_AIR.cp, gas_constant=STANDARD_AIR.R):
    return cp * math.log(T2 / T1) - gas_constant * math.log(P2 / P1)


def isentropic_temperature(T_in, P_out, P_in, gamma_value=STANDARD_AIR.gamma):
    return T_in * (P_out / P_in) ** ((gamma_value - 1.0) / gamma_value)


def pressure_from_isentropic_temperature(T_in, T_out, P_in, gamma_value=STANDARD_AIR.gamma):
    return P_in * (T_out / T_in) ** (gamma_value / (gamma_value - 1.0))


def fuel_air_ratio_for_target_temperature(T_out, T_in, gas, burner_efficiency=None):
    eta_b = burner_efficiency if burner_efficiency is not None else gas.burner_efficiency
    numerator = gas.cp * (T_out - T_in)
    denominator = eta_b * gas.lower_heating_value - gas.cp * T_out
    if denominator <= 0:
        return 0.0
    return max(0.0, numerator / denominator)


def critical_pressure_ratio(gamma_value=STANDARD_AIR.gamma):
    return (2.0 / (gamma_value + 1.0)) ** (gamma_value / (gamma_value - 1.0))


def nozzle_exit_state(T_total, P_total, ambient_pressure, gas, eta_n, m_dot):
    critical_ratio = critical_pressure_ratio(gas.gamma)
    critical_pressure = P_total * critical_ratio
    choked = ambient_pressure <= critical_pressure
    exit_pressure = critical_pressure if choked else ambient_pressure

    exit_temperature_isentropic = isentropic_temperature(T_total, exit_pressure, P_total, gas.gamma)
    exit_temperature = T_total - eta_n * (T_total - exit_temperature_isentropic)
    exit_velocity = math.sqrt(max(0.0, 2.0 * gas.cp * (T_total - exit_temperature)))
    density = exit_pressure / (gas.R * exit_temperature)
    exit_area = m_dot / max(density * max(exit_velocity, 1e-9), 1e-9)
    pressure_thrust = max(0.0, (exit_pressure - ambient_pressure) * exit_area)

    return {
        "temperature": exit_temperature,
        "pressure": exit_pressure,
        "velocity": exit_velocity,
        "exit_area": exit_area,
        "pressure_thrust": pressure_thrust,
        "choked": choked,
    }
