from copy import deepcopy

import pandas as pd

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from models.gas import build_gas_from_config
from performance.metrics import summarize_result
from solver.base import EngineRunResult, FlowState
from solver.helpers import kelvinToCelsius
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


def build_engine(config, gas):
    return Engine(
        [
            Inlet(
                pressure_recovery=config["pressure_recovery"],
                exit_velocity=config["diffuser_exit_velocity"],
                gas=gas,
            ),
            Compressor(
                pressure_ratio=config["compressor_pressure_ratio"],
                eta_c=config["compressor_efficiency"],
                gas=gas,
            ),
            Combustor(
                T3=config["turbine_inlet_temperature"],
                pressure_loss=config["combustor_pressure_loss"],
                gas=gas,
                burner_efficiency=config["combustor_efficiency"],
            ),
            Turbine(
                eta_t=config["turbine_efficiency"],
                eta_mech=config["mechanical_efficiency"],
                gas=gas,
            ),
            Nozzle(
                gas=gas,
                Pe=config["ambient_pressure"],
                eta_n=config["nozzle_efficiency"],
            ),
        ]
    )


def build_initial_state(config, gas):
    atmosphere = isa_atmosphere(config.get("altitude_m", 0.0))
    ambient_temperature = config.get("ambient_temperature", atmosphere.temperature)
    ambient_pressure = config.get("ambient_pressure", atmosphere.pressure)

    state0 = FlowState(
        T=ambient_temperature,
        P=ambient_pressure,
        V=config["flight_speed"],
        m_dot=config["mass_flow_rate"],
        gas=gas,
    )
    state0.stage_name = "Freestream"
    return state0


def run_engine_case(config=None):
    merged = get_default_config()
    if config:
        merged.update(config)

    gas = build_gas_from_config(merged)
    engine = build_engine(merged, gas)
    initial_state = build_initial_state(merged, gas)
    runtime_config = deepcopy(merged)
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
