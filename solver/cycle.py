"""Thermodynamic helper relations used by the cycle solver."""

import math

from models.atmosphere import Cp, R, gamma


def specific_volume(T, P, gas_constant=R):
    return gas_constant * T / P


def total_temperature(T, velocity, cp=Cp):
    return T + velocity**2 / (2.0 * cp)


def static_temperature_from_total(T_total, velocity, cp=Cp):
    return T_total - velocity**2 / (2.0 * cp)


def stagnation_pressure_from_static(T_static, P_static, T_total, gamma_value=gamma):
    return P_static * (T_total / T_static) ** (gamma_value / (gamma_value - 1.0))


def static_pressure_from_stagnation(T_static, T_total, P_total, gamma_value=gamma):
    return P_total * (T_static / T_total) ** (gamma_value / (gamma_value - 1.0))


def entropy_change(T2, T1, P2, P1, cp=Cp, gas_constant=R):
    return cp * math.log(T2 / T1) - gas_constant * math.log(P2 / P1)


def isentropic_temperature(T_in, P_out, P_in, gamma_value=gamma):
    return T_in * (P_out / P_in) ** ((gamma_value - 1.0) / gamma_value)


def pressure_from_isentropic_temperature(T_in, T_out, P_in, gamma_value=gamma):
    return P_in * (T_out / T_in) ** (gamma_value / (gamma_value - 1.0))
