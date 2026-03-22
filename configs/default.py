from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class EngineConfig:
    preset_name: str = "Turbojet"
    architecture: str = "turbojet"
    altitude_m: float = 0.0
    ambient_temperature: float | None = None
    ambient_pressure: float | None = None
    flight_input_mode: str = "speed"
    flight_speed: float = 200.0
    flight_mach_number: float = 0.0
    mass_flow_rate: float = 10.0
    pressure_recovery: float = 0.98
    diffuser_exit_velocity: float = 85.0
    bypass_ratio: float = 0.0
    fan_pressure_ratio: float = 1.55
    fan_efficiency: float = 0.89
    fan_exit_velocity: float = 135.0
    bypass_duct_pressure_loss: float = 0.02
    bypass_nozzle_efficiency: float = 0.98
    bypass_nozzle_type: str = "convergent"
    bypass_nozzle_pressure_loss: float = 0.01
    bypass_nozzle_throat_area: float | None = None
    bypass_nozzle_exit_area: float | None = None
    compressor_pressure_ratio: float = 10.0
    compressor_efficiency: float = 0.85
    compressor_exit_velocity: float = 120.0
    turbine_inlet_temperature: float = 1500.0
    combustor_pressure_loss: float = 0.05
    combustor_efficiency: float = 0.99
    combustor_exit_velocity: float = 70.0
    turbine_efficiency: float = 0.90
    mechanical_efficiency: float = 0.95
    hp_mechanical_efficiency: float = 0.95
    lp_mechanical_efficiency: float = 0.95
    hp_turbine_efficiency: float = 0.90
    lp_turbine_efficiency: float = 0.90
    turbine_exit_velocity: float = 150.0
    afterburner_enabled: bool = False
    afterburner_exit_temperature: float = 1800.0
    afterburner_pressure_loss: float = 0.04
    afterburner_efficiency: float = 0.98
    afterburner_exit_velocity: float = 170.0
    nozzle_efficiency: float = 0.97
    core_nozzle_type: str = "convergent"
    core_nozzle_pressure_loss: float = 0.01
    core_nozzle_throat_area: float | None = None
    core_nozzle_exit_area: float | None = None
    gas_name: str = "Air"
    gas_cp: float = 1005.0
    gas_gamma: float = 1.4
    gas_R: float | None = None
    gas_temperature_dependent: bool = True
    gas_reference_temperature: float = 300.0
    gas_cp_temperature_slope: float = 0.08
    fuel_lower_heating_value: float = 43_000_000.0
    component_maps_enabled: bool = True
    map_sensitivity_pressure_ratio: float = 0.06
    map_sensitivity_corrected_flow: float = 0.05
    turbine_map_sensitivity_loading: float = 0.05
    map_min_efficiency: float = 0.70
    fan_design_corrected_flow: float | None = None
    compressor_design_corrected_flow: float | None = None
    hp_turbine_design_loading: float = 0.22
    lp_turbine_design_loading: float = 0.24
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


PRESET_OVERRIDES: dict[str, dict[str, Any]] = {
    "Turbojet": {},
    "Afterburning Turbojet": {
        "preset_name": "Afterburning Turbojet",
        "afterburner_enabled": True,
        "afterburner_exit_temperature": 1950.0,
        "afterburner_pressure_loss": 0.05,
        "turbine_inlet_temperature": 1600.0,
    },
    "Low-Bypass Turbofan": {
        "preset_name": "Low-Bypass Turbofan",
        "architecture": "turbofan",
        "bypass_ratio": 1.6,
        "fan_pressure_ratio": 1.65,
        "compressor_pressure_ratio": 14.0,
        "mass_flow_rate": 24.0,
        "turbine_inlet_temperature": 1550.0,
        "hp_turbine_efficiency": 0.91,
        "lp_turbine_efficiency": 0.92,
        "fan_exit_velocity": 145.0,
        "turbine_exit_velocity": 165.0,
    },
    "High-Bypass Turbofan": {
        "preset_name": "High-Bypass Turbofan",
        "architecture": "turbofan",
        "bypass_ratio": 5.5,
        "fan_pressure_ratio": 1.45,
        "compressor_pressure_ratio": 18.0,
        "mass_flow_rate": 65.0,
        "turbine_inlet_temperature": 1650.0,
        "hp_turbine_efficiency": 0.92,
        "lp_turbine_efficiency": 0.93,
        "fan_exit_velocity": 150.0,
        "bypass_duct_pressure_loss": 0.015,
    },
}


def get_default_engine_config() -> EngineConfig:
    return EngineConfig()


def get_default_config() -> dict[str, Any]:
    return get_default_engine_config().to_dict()


def list_presets() -> list[str]:
    return list(PRESET_OVERRIDES.keys())


def get_preset_engine_config(name: str) -> EngineConfig:
    overrides = PRESET_OVERRIDES.get(name, {})
    return get_default_engine_config().updated(**overrides)


def get_preset_config(name: str) -> dict[str, Any]:
    return get_preset_engine_config(name).to_dict()
