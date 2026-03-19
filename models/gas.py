from dataclasses import dataclass


@dataclass(frozen=True)
class IdealGas:
    name: str = "Air"
    cp: float = 1005.0
    gamma: float = 1.4
    lower_heating_value: float = 43_000_000.0
    burner_efficiency: float = 0.99

    @property
    def R(self):
        return self.cp * (self.gamma - 1.0) / self.gamma


STANDARD_AIR = IdealGas()


def build_gas_from_config(config):
    return IdealGas(
        name=config.get("gas_name", "Air"),
        cp=config.get("gas_cp", STANDARD_AIR.cp),
        gamma=config.get("gas_gamma", STANDARD_AIR.gamma),
        lower_heating_value=config.get("fuel_lower_heating_value", STANDARD_AIR.lower_heating_value),
        burner_efficiency=config.get("combustor_efficiency", STANDARD_AIR.burner_efficiency),
    )
