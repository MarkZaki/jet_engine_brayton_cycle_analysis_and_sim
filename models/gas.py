from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from configs.default import EngineConfig


@dataclass(frozen=True)
class IdealGas:
    name: str = "Air"
    cp_reference: float = 1005.0
    gamma_reference: float = 1.4
    gas_constant: float = 287.05
    lower_heating_value: float = 43_000_000.0
    burner_efficiency: float = 0.99
    temperature_dependent: bool = True
    reference_temperature: float = 300.0
    cp_temperature_slope: float = 0.08

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
        if not self.temperature_dependent:
            return self.cp_reference
        return max(1.0, self.cp_reference + self.cp_temperature_slope * (temperature - self.reference_temperature))

    def gamma_at(self, temperature: float) -> float:
        cp_value = self.cp_at(temperature)
        return max(1.01, cp_value / max(cp_value - self.gas_constant, 1e-9))

    def delta_h(self, temperature_out: float, temperature_in: float) -> float:
        if not self.temperature_dependent:
            return self.cp_reference * (temperature_out - temperature_in)

        t_ref = self.reference_temperature
        linear_term = self.cp_reference * (temperature_out - temperature_in)
        quadratic_term = 0.5 * self.cp_temperature_slope * (
            (temperature_out - t_ref) ** 2 - (temperature_in - t_ref) ** 2
        )
        return linear_term + quadratic_term

    def cp_mean(self, temperature_in: float, temperature_out: float) -> float:
        delta_t = temperature_out - temperature_in
        if abs(delta_t) < 1e-12:
            return self.cp_at(temperature_in)
        return self.delta_h(temperature_out, temperature_in) / delta_t

    def gamma_mean(self, temperature_in: float, temperature_out: float) -> float:
        cp_value = self.cp_mean(temperature_in, temperature_out)
        return max(1.01, cp_value / max(cp_value - self.gas_constant, 1e-9))

    def temperature_from_enthalpy_change(self, temperature_in: float, delta_h: float) -> float:
        if not self.temperature_dependent:
            return temperature_in + delta_h / self.cp_reference

        t_ref = self.reference_temperature
        shifted_in = temperature_in - t_ref
        a = 0.5 * self.cp_temperature_slope
        b = self.cp_reference
        c = -(self.cp_reference * shifted_in + 0.5 * self.cp_temperature_slope * shifted_in**2 + delta_h)

        if abs(a) < 1e-12:
            shifted_out = -c / max(b, 1e-12)
        else:
            discriminant = max(0.0, b * b - 4.0 * a * c)
            root_1 = (-b + discriminant**0.5) / (2.0 * a)
            root_2 = (-b - discriminant**0.5) / (2.0 * a)
            candidates = [root for root in (root_1, root_2) if root > -t_ref + 1e-6]
            if not candidates:
                shifted_out = root_1
            else:
                shifted_out = min(candidates, key=lambda value: abs(value - shifted_in))

        return max(1.0, shifted_out + t_ref)


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
        temperature_dependent=bool(
            _config_lookup(config, "gas_temperature_dependent", STANDARD_AIR.temperature_dependent)
        ),
        reference_temperature=float(
            _config_lookup(config, "gas_reference_temperature", STANDARD_AIR.reference_temperature)
        ),
        cp_temperature_slope=float(
            _config_lookup(config, "gas_cp_temperature_slope", STANDARD_AIR.cp_temperature_slope)
        ),
    )
