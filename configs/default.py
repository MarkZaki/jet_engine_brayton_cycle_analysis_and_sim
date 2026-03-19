DEFAULT_CONFIG = {
    "altitude_m": 0.0,
    "ambient_temperature": 288.15,
    "ambient_pressure": 101325.0,
    "flight_speed": 200.0,
    "mass_flow_rate": 10.0,
    "pressure_recovery": 0.98,
    "diffuser_exit_velocity": 0.0,
    "compressor_pressure_ratio": 10.0,
    "compressor_efficiency": 0.85,
    "turbine_inlet_temperature": 1500.0,
    "combustor_pressure_loss": 0.05,
    "combustor_efficiency": 0.99,
    "turbine_efficiency": 0.90,
    "mechanical_efficiency": 0.95,
    "nozzle_efficiency": 0.97,
    "gas_name": "Air",
    "gas_cp": 1005.0,
    "gas_gamma": 1.4,
    "fuel_lower_heating_value": 43_000_000.0,
    "verbose": True,
}


def get_default_config():
    return dict(DEFAULT_CONFIG)
