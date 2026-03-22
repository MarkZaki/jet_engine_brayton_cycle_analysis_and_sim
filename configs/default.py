from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class EngineConfig:
    altitude_m: float = 0.0
    ambient_temperature: float | None = None
    ambient_pressure: float | None = None
    flight_input_mode: str = "speed"
    flight_speed: float = 180.0
    flight_mach_number: float = 0.0
    mass_flow_rate: float = 12.0
    pressure_recovery: float = 0.98
    diffuser_exit_velocity: float = 60.0
    compressor_pressure_ratio: float = 8.0
    compressor_efficiency: float = 0.85
    compressor_exit_velocity: float = 70.0
    turbine_inlet_temperature: float = 1400.0
    combustor_pressure_loss: float = 0.05
    combustor_efficiency: float = 0.98
    combustor_exit_velocity: float = 45.0
    turbine_efficiency: float = 0.90
    mechanical_efficiency: float = 0.97
    turbine_exit_velocity: float = 85.0
    nozzle_efficiency: float = 0.96
    gas_name: str = "Air"
    gas_cp: float = 1004.5
    gas_gamma: float = 1.4
    gas_R: float | None = None
    fuel_lower_heating_value: float = 43_000_000.0
    export_png: bool = False
    verbose: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None = None) -> "EngineConfig":
        if values is None:
            return cls()
        valid_keys = {field.name for field in fields(cls)}
        filtered = {key: value for key, value in dict(values).items() if key in valid_keys}
        return cls(**filtered)

    def updated(self, **overrides: Any) -> "EngineConfig":
        valid_keys = {field.name for field in fields(type(self))}
        filtered = {key: value for key, value in overrides.items() if key in valid_keys}
        return replace(self, **filtered)

def get_default_engine_config() -> EngineConfig:
    return EngineConfig()


def get_default_config() -> dict[str, Any]:
    return get_default_engine_config().to_dict()
