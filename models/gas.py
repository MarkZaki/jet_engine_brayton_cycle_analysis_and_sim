from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from configs.default import EngineConfig


@dataclass(frozen=True)
class IdealGas:
    name: str = "Air"
    cp_reference: float = 1004.5
    gamma_reference: float = 1.4
    gas_constant: float = 287.05
    lower_heating_value: float = 43_000_000.0
    burner_efficiency: float = 0.98

    @property
    def cp(self) -> float:
        return self.cp_reference

    @property
    def gamma(self) -> float:
        return self.gamma_reference

    @property
    def R(self) -> float:
        return self.gas_constant

    def cp_at(self, temperature: float) -> float:
        return self.cp_reference

    def gamma_at(self, temperature: float) -> float:
        return self.gamma_reference

    def delta_h(self, temperature_out: float, temperature_in: float) -> float:
        return self.cp_reference * (temperature_out - temperature_in)

    def cp_mean(self, temperature_in: float, temperature_out: float) -> float:
        return self.cp_reference

    def gamma_mean(self, temperature_in: float, temperature_out: float) -> float:
        return self.gamma_reference

    def temperature_from_enthalpy_change(self, temperature_in: float, delta_h: float) -> float:
        return max(1.0, temperature_in + delta_h / self.cp_reference)


STANDARD_AIR = IdealGas()


def _config_lookup(config: EngineConfig | Mapping[str, Any], key: str, default: Any) -> Any:
    if isinstance(config, EngineConfig):
        return getattr(config, key, default)
    return config.get(key, default)


def build_gas_from_config(config: EngineConfig | Mapping[str, Any]) -> IdealGas:
    gamma_value = float(_config_lookup(config, "gas_gamma", STANDARD_AIR.gamma_reference))
    cp_value = float(_config_lookup(config, "gas_cp", STANDARD_AIR.cp_reference))
    default_r = cp_value * (gamma_value - 1.0) / gamma_value
    configured_r = _config_lookup(config, "gas_R", None)
    gas_constant = float(default_r if configured_r is None else configured_r)

    return IdealGas(
        name=str(_config_lookup(config, "gas_name", STANDARD_AIR.name)),
        cp_reference=cp_value,
        gamma_reference=gamma_value,
        gas_constant=gas_constant,
        lower_heating_value=float(
            _config_lookup(config, "fuel_lower_heating_value", STANDARD_AIR.lower_heating_value)
        ),
        burner_efficiency=float(
            _config_lookup(config, "combustor_efficiency", STANDARD_AIR.burner_efficiency)
        ),
    )
