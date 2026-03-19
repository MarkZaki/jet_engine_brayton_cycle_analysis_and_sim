"""Thermodynamic helper relations used by the cycle solver."""

import math

from models.gas import STANDARD_AIR


def specific_volume(T, P, gas_constant=STANDARD_AIR.R):
    return gas_constant * T / P


def density(T, P, gas_constant=STANDARD_AIR.R):
    return P / (gas_constant * T)


def speed_of_sound(T, gamma_value=STANDARD_AIR.gamma, gas_constant=STANDARD_AIR.R):
    return math.sqrt(max(1e-12, gamma_value * gas_constant * T))


def mach_number(velocity, T, gamma_value=STANDARD_AIR.gamma, gas_constant=STANDARD_AIR.R):
    return velocity / max(speed_of_sound(T, gamma_value, gas_constant), 1e-12)


def total_temperature(T, velocity, cp=STANDARD_AIR.cp):
    return T + velocity**2 / (2.0 * cp)


def static_temperature_from_total(T_total, velocity, cp=STANDARD_AIR.cp):
    return max(1e-9, T_total - velocity**2 / (2.0 * cp))


def stagnation_pressure_from_static(T_static, P_static, T_total, gamma_value=STANDARD_AIR.gamma):
    return P_static * (T_total / T_static) ** (gamma_value / (gamma_value - 1.0))


def static_pressure_from_stagnation(T_static, T_total, P_total, gamma_value=STANDARD_AIR.gamma):
    return P_total * (T_static / T_total) ** (gamma_value / (gamma_value - 1.0))


def static_state_from_total_and_velocity(T_total, P_total, velocity, gas):
    T_static = static_temperature_from_total(T_total, velocity, gas.cp)
    P_static = static_pressure_from_stagnation(T_static, T_total, P_total, gas.gamma)
    return {
        "temperature": T_static,
        "pressure": P_static,
        "density": density(T_static, P_static, gas.R),
        "specific_volume": specific_volume(T_static, P_static, gas.R),
        "mach": mach_number(velocity, T_static, gas.gamma, gas.R),
    }


def stagnation_state_from_static(T_static, P_static, velocity, gas):
    T_total = total_temperature(T_static, velocity, gas.cp)
    P_total = stagnation_pressure_from_static(T_static, P_static, T_total, gas.gamma)
    return {
        "temperature": T_total,
        "pressure": P_total,
        "mach": mach_number(velocity, T_static, gas.gamma, gas.R),
    }


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


def choked_area_from_total_state(T_total, P_total, gas, m_dot):
    T_star = T_total * 2.0 / (gas.gamma + 1.0)
    P_star = P_total * critical_pressure_ratio(gas.gamma)
    rho_star = density(T_star, P_star, gas.R)
    velocity_star = speed_of_sound(T_star, gas.gamma, gas.R)
    throat_area = m_dot / max(rho_star * velocity_star, 1e-9)
    return {
        "temperature": T_star,
        "pressure": P_star,
        "density": rho_star,
        "velocity": velocity_star,
        "area": throat_area,
    }


def flow_area(m_dot, rho, velocity):
    return m_dot / max(rho * max(velocity, 1e-9), 1e-9)


def nozzle_exit_state(T_total, P_total, ambient_pressure, gas, eta_n, m_dot):
    critical_ratio = critical_pressure_ratio(gas.gamma)
    critical_pressure = P_total * critical_ratio
    choked = ambient_pressure <= critical_pressure
    exit_pressure = critical_pressure if choked else ambient_pressure

    exit_temperature_isentropic = isentropic_temperature(T_total, exit_pressure, P_total, gas.gamma)
    exit_temperature = T_total - eta_n * (T_total - exit_temperature_isentropic)
    exit_velocity = math.sqrt(max(0.0, 2.0 * gas.cp * (T_total - exit_temperature)))
    rho_exit = density(exit_temperature, exit_pressure, gas.R)
    exit_area = flow_area(m_dot, rho_exit, exit_velocity)
    throat = choked_area_from_total_state(T_total, P_total, gas, m_dot)
    pressure_thrust = (exit_pressure - ambient_pressure) * exit_area

    return {
        "temperature": exit_temperature,
        "pressure": exit_pressure,
        "velocity": exit_velocity,
        "density": rho_exit,
        "mach": mach_number(exit_velocity, exit_temperature, gas.gamma, gas.R),
        "exit_area": exit_area,
        "throat_area": throat["area"],
        "pressure_thrust": pressure_thrust,
        "choked": choked,
    }
