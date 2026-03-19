from dataclasses import dataclass

from models.gas import STANDARD_AIR

Cp = STANDARD_AIR.cp
gamma = STANDARD_AIR.gamma
R = STANDARD_AIR.R


@dataclass(frozen=True)
class AtmosphereState:
    altitude_m: float
    temperature: float
    pressure: float
    density: float


def isa_atmosphere(altitude_m):
    altitude = max(0.0, altitude_m)
    g0 = 9.80665
    troposphere_lapse = 0.0065
    T0 = 288.15
    P0 = 101325.0

    if altitude <= 11_000.0:
        temperature = T0 - troposphere_lapse * altitude
        pressure = P0 * (temperature / T0) ** (g0 / (R * troposphere_lapse))
    else:
        temperature = 216.65
        pressure_11 = P0 * (temperature / T0) ** (g0 / (R * troposphere_lapse))
        pressure = pressure_11 * 2.718281828459045 ** (
            -g0 * (altitude - 11_000.0) / (R * temperature)
        )

    density = pressure / (R * temperature)
    return AtmosphereState(
        altitude_m=altitude,
        temperature=temperature,
        pressure=pressure,
        density=density,
    )
