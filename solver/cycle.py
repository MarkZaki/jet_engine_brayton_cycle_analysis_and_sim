"""Thermodynamic helper relations used by the cycle solver."""

import math

from models.atmosphere import Cp, R, gamma


def specific_volume(T, P, gas_constant=R):
    return gas_constant * T / P


def entropy_change(T2, T1, P2, P1, cp=Cp, gas_constant=R):
    return cp * math.log(T2 / T1) - gas_constant * math.log(P2 / P1)


def isentropic_temperature(T_in, P_out, P_in, gamma_value=gamma):
    return T_in * (P_out / P_in) ** ((gamma_value - 1.0) / gamma_value)


def pressure_from_isentropic_temperature(T_in, T_out, P_in, gamma_value=gamma):
    return P_in * (T_out / T_in) ** (gamma_value / (gamma_value - 1.0))
