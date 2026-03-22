from copy import deepcopy

import pandas as pd

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from models.gas import build_gas_from_config
from performance.metrics import summarize_result
from solver.base import EngineRunResult, FlowState
from solver.helpers import kelvinToCelsius
from solver.stages.afterburner import Afterburner
from solver.stages.combustor import Combustor
from solver.stages.compressor import Compressor
from solver.stages.inlet import Inlet
from solver.stages.nozzle import Nozzle
from solver.stages.turbine import Turbine


class Engine:
    def __init__(self, stages):
        self.stages = stages

    def run(self, initial_state, verbose=True, config=None):
        initial_state.update_derived()
        states = [initial_state]

        for index, stage in enumerate(self.stages):
            new_state = stage.process(states[-1])
            new_state.stage_name = stage.name
            new_state.stage_index = index
            new_state.update_derived()
            states.append(new_state)

            if verbose:
                print(
                    f"{stage.name}: "
                    f"actual T={kelvinToCelsius(new_state.T):.2f} degC, "
                    f"actual P={new_state.P:.0f} Pa | "
                    f"ideal T={kelvinToCelsius(new_state.T_ideal):.2f} degC, "
                    f"ideal P={new_state.P_ideal:.0f} Pa"
                )

        return EngineRunResult(states=states, gas=initial_state.gas, config=config or {})


def _resolve_ambient_conditions(config):
    resolved = deepcopy(config)
    atmosphere = isa_atmosphere(resolved.get("altitude_m", 0.0))
    if resolved.get("ambient_temperature") is None:
        resolved["ambient_temperature"] = atmosphere.temperature
    if resolved.get("ambient_pressure") is None:
        resolved["ambient_pressure"] = atmosphere.pressure
    return resolved


def _validate_closed_interval(name, value, lower, upper):
    if not (lower <= value <= upper):
        raise ValueError(f"{name} must be between {lower} and {upper}.")

def validate_config(config):
    if config["altitude_m"] < 0.0:
        raise ValueError("altitude_m must be non-negative.")
    if config["flight_speed"] < 0.0:
        raise ValueError("flight_speed must be non-negative.")
    if config["mass_flow_rate"] <= 0.0:
        raise ValueError("mass_flow_rate must be greater than zero.")
    if config["gas_cp"] <= 0.0:
        raise ValueError("gas_cp must be greater than zero.")
    if config["gas_gamma"] <= 1.0:
        raise ValueError("gas_gamma must be greater than 1.")
    if config["fuel_lower_heating_value"] <= 0.0:
        raise ValueError("fuel_lower_heating_value must be greater than zero.")
    if config["ambient_temperature"] <= 0.0:
        raise ValueError("ambient_temperature must be greater than zero.")
    if config["ambient_pressure"] <= 0.0:
        raise ValueError("ambient_pressure must be greater than zero.")
    if config["turbine_inlet_temperature"] <= 0.0:
        raise ValueError("turbine_inlet_temperature must be greater than zero.")
    if config["afterburner_exit_temperature"] <= 0.0:
        raise ValueError("afterburner_exit_temperature must be greater than zero.")

    _validate_closed_interval("pressure_recovery", config["pressure_recovery"], 0.0, 1.0)
    for key in (
        "compressor_efficiency",
        "combustor_efficiency",
        "turbine_efficiency",
        "mechanical_efficiency",
        "afterburner_efficiency",
        "nozzle_efficiency",
    ):
        if not (0.0 < config[key] <= 1.0):
            raise ValueError(f"{key} must be greater than 0 and at most 1.")

    if not (0.0 <= config["combustor_pressure_loss"] < 1.0):
        raise ValueError("combustor_pressure_loss must be between 0 and 1.")
    if not (0.0 <= config["afterburner_pressure_loss"] < 1.0):
        raise ValueError("afterburner_pressure_loss must be between 0 and 1.")
    if config["compressor_pressure_ratio"] < 1.0:
        raise ValueError("compressor_pressure_ratio must be at least 1.")

    for key in (
        "diffuser_exit_velocity",
        "compressor_exit_velocity",
        "combustor_exit_velocity",
        "turbine_exit_velocity",
        "afterburner_exit_velocity",
    ):
        if config[key] < 0.0:
            raise ValueError(f"{key} must be non-negative.")


def prepare_config(config=None):
    merged = get_default_config()
    if config:
        merged.update(config)
    resolved = _resolve_ambient_conditions(merged)
    validate_config(resolved)
    return resolved


def build_engine(config, gas):
    stages = [
        Inlet(
            pressure_recovery=config["pressure_recovery"],
            exit_velocity=config["diffuser_exit_velocity"],
            gas=gas,
        ),
        Compressor(
            pressure_ratio=config["compressor_pressure_ratio"],
            eta_c=config["compressor_efficiency"],
            exit_velocity=config["compressor_exit_velocity"],
            gas=gas,
        ),
        Combustor(
            T3=config["turbine_inlet_temperature"],
            pressure_loss=config["combustor_pressure_loss"],
            exit_velocity=config["combustor_exit_velocity"],
            gas=gas,
            burner_efficiency=config["combustor_efficiency"],
        ),
        Turbine(
            eta_t=config["turbine_efficiency"],
            eta_mech=config["mechanical_efficiency"],
            exit_velocity=config["turbine_exit_velocity"],
            gas=gas,
        ),
    ]
    if config.get("afterburner_enabled", False):
        stages.append(
            Afterburner(
                Tt_out=config["afterburner_exit_temperature"],
                pressure_loss=config["afterburner_pressure_loss"],
                exit_velocity=config["afterburner_exit_velocity"],
                gas=gas,
                burner_efficiency=config["afterburner_efficiency"],
            )
        )

    stages.append(
        Nozzle(
            gas=gas,
            Pe=config["ambient_pressure"],
            eta_n=config["nozzle_efficiency"],
        )
    )
    return Engine(stages)


def build_initial_state(config, gas):
    state0 = FlowState(
        T=config["ambient_temperature"],
        P=config["ambient_pressure"],
        V=config["flight_speed"],
        m_dot=config["mass_flow_rate"],
        gas=gas,
    )
    state0.stage_name = "Freestream"
    return state0


def run_engine_case(config=None):
    runtime_config = prepare_config(config)
    gas = build_gas_from_config(runtime_config)
    engine = build_engine(runtime_config, gas)
    initial_state = build_initial_state(runtime_config, gas)
    return engine.run(initial_state, verbose=runtime_config.get("verbose", False), config=runtime_config)


def sweep_compressor_pressure_ratio(base_config, pressure_ratios):
    rows = []

    for pressure_ratio in pressure_ratios:
        case_config = deepcopy(base_config)
        case_config["compressor_pressure_ratio"] = float(pressure_ratio)
        case_config["verbose"] = False
        result = run_engine_case(case_config)
        summary = summarize_result(result, V0=case_config["flight_speed"])
        rows.append(
            {
                "compressor_pressure_ratio": pressure_ratio,
                "thrust_N": summary["thrust_N"],
                "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                "fuel_air_ratio": summary["fuel_air_ratio"],
                "shaft_efficiency": summary["shaft_efficiency"],
                "jet_power_efficiency": summary["jet_power_efficiency"],
                "overall_efficiency": summary["overall_efficiency"],
                "exit_velocity_mps": summary["exit_velocity_mps"],
                "nozzle_choked": summary["nozzle_choked"],
            }
        )

    return pd.DataFrame(rows)


def sweep_flight_envelope(base_config, altitudes_m, flight_speeds_mps):
    rows = []

    for altitude_m in altitudes_m:
        atmosphere = isa_atmosphere(float(altitude_m))
        for flight_speed in flight_speeds_mps:
            case_config = deepcopy(base_config)
            case_config["altitude_m"] = float(altitude_m)
            case_config["ambient_temperature"] = atmosphere.temperature
            case_config["ambient_pressure"] = atmosphere.pressure
            case_config["flight_speed"] = float(flight_speed)
            case_config["verbose"] = False
            result = run_engine_case(case_config)
            summary = summarize_result(result, V0=case_config["flight_speed"])
            rows.append(
                {
                    "altitude_m": float(altitude_m),
                    "flight_speed_mps": float(flight_speed),
                    "thrust_N": summary["thrust_N"],
                    "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                    "overall_efficiency": summary["overall_efficiency"],
                    "jet_power_efficiency": summary["jet_power_efficiency"],
                    "nozzle_choked": summary["nozzle_choked"],
                }
            )

    return pd.DataFrame(rows)
