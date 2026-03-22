from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

import pandas as pd

from configs.default import (
    EngineConfig,
    get_default_engine_config,
    get_preset_engine_config,
    list_presets,
)
from models.atmosphere import isa_atmosphere
from models.gas import build_gas_from_config
from performance.metrics import summarize_result
from solver.base import EngineRunResult, FlowState
from solver.cycle import nozzle_exit_state, speed_of_sound
from solver.helpers import kelvinToCelsius
from solver.stages.afterburner import Afterburner
from solver.stages.combustor import Combustor
from solver.stages.compressor import Compressor
from solver.stages.inlet import Inlet
from solver.stages.nozzle import Nozzle
from solver.stages.turbine import Turbine


ENGINE_ASSUMPTIONS = [
    "The model is one-dimensional and station-based, not CFD.",
    "Gas properties may vary with temperature using a linear cp(T) approximation.",
    "Turbofan mode uses separate core and bypass nozzles with a simple bypass duct model.",
    "Component maps are simplified off-design efficiency schedules, not manufacturer maps.",
    "Theoretical branches neglect map penalties, mechanical losses, and burner pressure loss where appropriate.",
]

ENGINE_EQUATIONS = [
    "Tt = T + V^2 / (2 cp_eff)",
    "Pt/P = (Tt/T)^(gamma_eff/(gamma_eff-1))",
    "f = Delta_h / (eta_b LHV - cp(T_out) T_out)",
    "F = m_core,exit V_core + m_bypass V_bypass - m_air,total V0 + pressure thrust",
    "TSFC = m_fuel / F",
]


class Engine:
    def __init__(self, stages, gas, config: EngineConfig):
        self.stages = stages
        self.gas = gas
        self.config = config

    def _solve_bypass_stream(self, fan_state: FlowState) -> dict[str, Any]:
        if self.config.architecture != "turbofan" or fan_state.bypass_air_mass_flow <= 0.0:
            return {
                "exit_velocity_mps": 0.0,
                "exit_mach": 0.0,
                "exit_area_m2": 0.0,
                "throat_area_m2": 0.0,
                "pressure_thrust_N": 0.0,
                "nozzle_choked": False,
                "feasible": True,
                "continuity_error": 0.0,
                "message": "",
            }

        bypass_result = nozzle_exit_state(
            fan_state.Tt,
            fan_state.Pt * (1.0 - self.config.bypass_duct_pressure_loss),
            self.config.ambient_pressure if self.config.ambient_pressure is not None else 101325.0,
            self.gas,
            self.config.bypass_nozzle_efficiency,
            fan_state.bypass_air_mass_flow,
            nozzle_type=self.config.bypass_nozzle_type,
            throat_area=self.config.bypass_nozzle_throat_area,
            exit_area=self.config.bypass_nozzle_exit_area,
            total_pressure_loss=self.config.bypass_nozzle_pressure_loss,
        )
        return {
            "exit_velocity_mps": float(bypass_result["velocity"]),
            "exit_mach": float(bypass_result["mach"]),
            "exit_area_m2": float(bypass_result["exit_area"]),
            "throat_area_m2": float(bypass_result["throat_area"]),
            "pressure_thrust_N": float(bypass_result["pressure_thrust"]),
            "nozzle_choked": bool(bypass_result["choked"]),
            "feasible": bool(bypass_result["feasible"]),
            "message": str(bypass_result["message"]),
            "continuity_error": float(bypass_result["continuity_error"]),
        }

    def run(self, initial_state: FlowState, verbose: bool = True) -> EngineRunResult:
        initial_state.update_derived()
        states = [initial_state]
        fan_state: FlowState | None = None

        for index, stage in enumerate(self.stages):
            new_state = stage.process(states[-1])
            new_state.stage_name = stage.name
            new_state.stage_index = index
            new_state.update_derived()
            if stage.name == "Fan":
                fan_state = new_state.copy()
            states.append(new_state)

            if verbose:
                print(
                    f"{stage.name}: "
                    f"actual T={kelvinToCelsius(new_state.T):.2f} degC, "
                    f"actual P={new_state.P:.0f} Pa | "
                    f"ideal T={kelvinToCelsius(new_state.T_ideal):.2f} degC, "
                    f"ideal P={new_state.P_ideal:.0f} Pa"
                )

        final_state = states[-1]
        final_state.total_air_mass_flow = initial_state.total_air_mass_flow
        final_state.bypass_air_mass_flow = initial_state.bypass_air_mass_flow

        bypass_metrics = self._solve_bypass_stream(fan_state or initial_state)
        final_state.bypass_exit_velocity = bypass_metrics["exit_velocity_mps"]
        final_state.bypass_exit_mach = bypass_metrics["exit_mach"]
        final_state.bypass_exit_area = bypass_metrics["exit_area_m2"]
        final_state.bypass_throat_area = bypass_metrics["throat_area_m2"]
        final_state.bypass_pressure_thrust = bypass_metrics["pressure_thrust_N"]
        final_state.bypass_nozzle_choked = bypass_metrics["nozzle_choked"]
        if not bypass_metrics["feasible"]:
            final_state.mark_infeasible(bypass_metrics["message"])
        elif abs(bypass_metrics["continuity_error"]) > 0.03:
            final_state.add_warning(
                f"Bypass nozzle continuity mismatch is {bypass_metrics['continuity_error']:.1%}."
            )

        extras = {
            "architecture": self.config.architecture,
            "preset_name": self.config.preset_name,
            "bypass": bypass_metrics,
            "flight_mode": self.config.flight_input_mode,
        }
        return EngineRunResult(
            states=states,
            gas=initial_state.gas,
            config=asdict(self.config),
            extras=extras,
            assumptions=ENGINE_ASSUMPTIONS,
            equations=ENGINE_EQUATIONS,
        )


def _coerce_config(config: EngineConfig | Mapping[str, Any] | None) -> EngineConfig:
    if isinstance(config, EngineConfig):
        return config

    values = dict(config or {})
    preset_name = values.get("preset_name")
    if isinstance(preset_name, str) and preset_name in list_presets():
        base = get_preset_engine_config(preset_name)
    else:
        base = get_default_engine_config()
    return base.updated(**values)


def _resolve_ambient_conditions(config: EngineConfig) -> EngineConfig:
    atmosphere = isa_atmosphere(config.altitude_m)
    ambient_temperature = config.ambient_temperature if config.ambient_temperature is not None else atmosphere.temperature
    ambient_pressure = config.ambient_pressure if config.ambient_pressure is not None else atmosphere.pressure

    if config.flight_input_mode == "mach":
        flight_speed = config.flight_mach_number * speed_of_sound(ambient_temperature, build_gas_from_config(config))
    else:
        flight_speed = config.flight_speed

    core_mass_flow = config.mass_flow_rate / (1.0 + max(config.bypass_ratio, 0.0))
    return config.updated(
        ambient_temperature=ambient_temperature,
        ambient_pressure=ambient_pressure,
        flight_speed=flight_speed,
        fan_design_corrected_flow=config.fan_design_corrected_flow if config.fan_design_corrected_flow is not None else config.mass_flow_rate,
        compressor_design_corrected_flow=(
            config.compressor_design_corrected_flow if config.compressor_design_corrected_flow is not None else core_mass_flow
        ),
    )


def validate_config(config: EngineConfig) -> None:
    if config.preset_name and config.preset_name not in list_presets():
        pass
    if config.architecture not in {"turbojet", "turbofan"}:
        raise ValueError("architecture must be either 'turbojet' or 'turbofan'.")
    if config.flight_input_mode not in {"speed", "mach"}:
        raise ValueError("flight_input_mode must be either 'speed' or 'mach'.")
    if config.core_nozzle_type not in {"convergent", "converging-diverging"}:
        raise ValueError("core_nozzle_type must be 'convergent' or 'converging-diverging'.")
    if config.bypass_nozzle_type not in {"convergent", "converging-diverging"}:
        raise ValueError("bypass_nozzle_type must be 'convergent' or 'converging-diverging'.")
    if config.altitude_m < 0.0:
        raise ValueError("altitude_m must be non-negative.")
    if config.flight_speed < 0.0 or config.flight_mach_number < 0.0:
        raise ValueError("flight speed and Mach number must be non-negative.")
    if config.mass_flow_rate <= 0.0:
        raise ValueError("mass_flow_rate must be greater than zero.")
    if config.bypass_ratio < 0.0:
        raise ValueError("bypass_ratio must be non-negative.")
    if config.architecture == "turbofan" and config.bypass_ratio <= 0.0:
        raise ValueError("turbofan architecture requires bypass_ratio > 0.")
    if config.gas_cp <= 0.0 or config.gas_gamma <= 1.0:
        raise ValueError("gas properties are invalid.")
    if config.gas_R is not None and config.gas_R <= 0.0:
        raise ValueError("gas_R must be positive when provided.")
    if config.fuel_lower_heating_value <= 0.0:
        raise ValueError("fuel_lower_heating_value must be greater than zero.")
    if (config.ambient_temperature or 1.0) <= 0.0 or (config.ambient_pressure or 1.0) <= 0.0:
        raise ValueError("ambient conditions must be positive.")
    if config.turbine_inlet_temperature <= 0.0 or config.afterburner_exit_temperature <= 0.0:
        raise ValueError("combustor target temperatures must be positive.")

    if config.pressure_recovery < 0.0 or config.pressure_recovery > 1.0:
        raise ValueError("pressure_recovery must be between 0 and 1.")
    for value, label in (
        (config.combustor_pressure_loss, "combustor_pressure_loss"),
        (config.afterburner_pressure_loss, "afterburner_pressure_loss"),
        (config.bypass_duct_pressure_loss, "bypass_duct_pressure_loss"),
        (config.core_nozzle_pressure_loss, "core_nozzle_pressure_loss"),
        (config.bypass_nozzle_pressure_loss, "bypass_nozzle_pressure_loss"),
    ):
        if value < 0.0 or value >= 1.0:
            raise ValueError(f"{label} must be between 0 and 1.")

    for value, label in (
        (config.compressor_efficiency, "compressor_efficiency"),
        (config.combustor_efficiency, "combustor_efficiency"),
        (config.turbine_efficiency, "turbine_efficiency"),
        (config.mechanical_efficiency, "mechanical_efficiency"),
        (config.hp_mechanical_efficiency, "hp_mechanical_efficiency"),
        (config.lp_mechanical_efficiency, "lp_mechanical_efficiency"),
        (config.hp_turbine_efficiency, "hp_turbine_efficiency"),
        (config.lp_turbine_efficiency, "lp_turbine_efficiency"),
        (config.afterburner_efficiency, "afterburner_efficiency"),
        (config.nozzle_efficiency, "nozzle_efficiency"),
        (config.bypass_nozzle_efficiency, "bypass_nozzle_efficiency"),
        (config.fan_efficiency, "fan_efficiency"),
    ):
        if value <= 0.0 or value > 1.0:
            raise ValueError(f"{label} must be greater than 0 and at most 1.")

    for value, label in (
        (config.diffuser_exit_velocity, "diffuser_exit_velocity"),
        (config.fan_exit_velocity, "fan_exit_velocity"),
        (config.compressor_exit_velocity, "compressor_exit_velocity"),
        (config.combustor_exit_velocity, "combustor_exit_velocity"),
        (config.turbine_exit_velocity, "turbine_exit_velocity"),
        (config.afterburner_exit_velocity, "afterburner_exit_velocity"),
    ):
        if value < 0.0:
            raise ValueError(f"{label} must be non-negative.")

    if config.compressor_pressure_ratio < 1.0 or config.fan_pressure_ratio < 1.0:
        raise ValueError("compressor and fan pressure ratios must be at least 1.")


def prepare_config(config: EngineConfig | Mapping[str, Any] | None = None) -> EngineConfig:
    resolved = _resolve_ambient_conditions(_coerce_config(config))
    validate_config(resolved)
    return resolved


def build_engine(config: EngineConfig, gas):
    stages = [
        Inlet(
            pressure_recovery=config.pressure_recovery,
            exit_velocity=config.diffuser_exit_velocity,
            gas=gas,
        ),
    ]

    if config.architecture == "turbofan":
        stages.append(
            Compressor(
                pressure_ratio=config.fan_pressure_ratio,
                eta_c=config.fan_efficiency,
                exit_velocity=config.fan_exit_velocity,
                gas=gas,
                name="Fan",
                work_key="fan",
                map_enabled=config.component_maps_enabled,
                design_pressure_ratio=config.fan_pressure_ratio,
                design_corrected_flow=config.fan_design_corrected_flow,
                map_stream="total",
                map_sensitivity_pressure_ratio=config.map_sensitivity_pressure_ratio,
                map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                min_map_efficiency=config.map_min_efficiency,
            )
        )
        stages.append(
            Compressor(
                pressure_ratio=config.compressor_pressure_ratio,
                eta_c=config.compressor_efficiency,
                exit_velocity=config.compressor_exit_velocity,
                gas=gas,
                name="HP Compressor",
                work_key="hp_compressor",
                map_enabled=config.component_maps_enabled,
                design_pressure_ratio=config.compressor_pressure_ratio,
                design_corrected_flow=config.compressor_design_corrected_flow,
                map_stream="core",
                map_sensitivity_pressure_ratio=config.map_sensitivity_pressure_ratio,
                map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                min_map_efficiency=config.map_min_efficiency,
            )
        )
    else:
        stages.append(
            Compressor(
                pressure_ratio=config.compressor_pressure_ratio,
                eta_c=config.compressor_efficiency,
                exit_velocity=config.compressor_exit_velocity,
                gas=gas,
                name="Compressor",
                work_key="compressor",
                map_enabled=config.component_maps_enabled,
                design_pressure_ratio=config.compressor_pressure_ratio,
                design_corrected_flow=config.compressor_design_corrected_flow,
                map_stream="core",
                map_sensitivity_pressure_ratio=config.map_sensitivity_pressure_ratio,
                map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                min_map_efficiency=config.map_min_efficiency,
            )
        )

    stages.append(
        Combustor(
            T3=config.turbine_inlet_temperature,
            pressure_loss=config.combustor_pressure_loss,
            exit_velocity=config.combustor_exit_velocity,
            gas=gas,
            burner_efficiency=config.combustor_efficiency,
        )
    )

    if config.architecture == "turbofan":
        stages.extend(
            [
                Turbine(
                    eta_t=config.hp_turbine_efficiency,
                    eta_mech=config.hp_mechanical_efficiency,
                    exit_velocity=config.turbine_exit_velocity,
                    gas=gas,
                    name="HP Turbine",
                    load_keys=("hp_compressor",),
                    map_enabled=config.component_maps_enabled,
                    design_loading=config.hp_turbine_design_loading,
                    map_sensitivity_loading=config.turbine_map_sensitivity_loading,
                    map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                    min_map_efficiency=config.map_min_efficiency,
                ),
                Turbine(
                    eta_t=config.lp_turbine_efficiency,
                    eta_mech=config.lp_mechanical_efficiency,
                    exit_velocity=config.turbine_exit_velocity,
                    gas=gas,
                    name="LP Turbine",
                    load_keys=("fan",),
                    map_enabled=config.component_maps_enabled,
                    design_loading=config.lp_turbine_design_loading,
                    map_sensitivity_loading=config.turbine_map_sensitivity_loading,
                    map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                    min_map_efficiency=config.map_min_efficiency,
                ),
            ]
        )
    else:
        stages.append(
            Turbine(
                eta_t=config.turbine_efficiency,
                eta_mech=config.mechanical_efficiency,
                exit_velocity=config.turbine_exit_velocity,
                gas=gas,
                name="Turbine",
                load_keys=("compressor",),
                map_enabled=config.component_maps_enabled,
                design_loading=config.hp_turbine_design_loading,
                map_sensitivity_loading=config.turbine_map_sensitivity_loading,
                map_sensitivity_corrected_flow=config.map_sensitivity_corrected_flow,
                min_map_efficiency=config.map_min_efficiency,
            )
        )

    if config.afterburner_enabled:
        stages.append(
            Afterburner(
                Tt_out=config.afterburner_exit_temperature,
                pressure_loss=config.afterburner_pressure_loss,
                exit_velocity=config.afterburner_exit_velocity,
                gas=gas,
                burner_efficiency=config.afterburner_efficiency,
            )
        )

    stages.append(
        Nozzle(
            gas=gas,
            Pe=config.ambient_pressure if config.ambient_pressure is not None else 101325.0,
            eta_n=config.nozzle_efficiency,
            nozzle_type=config.core_nozzle_type,
            throat_area=config.core_nozzle_throat_area,
            exit_area=config.core_nozzle_exit_area,
            pressure_loss=config.core_nozzle_pressure_loss,
            name="Core Nozzle" if config.architecture == "turbofan" else "Nozzle",
        )
    )
    return Engine(stages, gas, config)


def build_initial_state(config: EngineConfig, gas) -> FlowState:
    core_mass_flow = config.mass_flow_rate / (1.0 + config.bypass_ratio) if config.architecture == "turbofan" else config.mass_flow_rate
    state0 = FlowState(
        T=config.ambient_temperature if config.ambient_temperature is not None else 288.15,
        P=config.ambient_pressure if config.ambient_pressure is not None else 101325.0,
        V=config.flight_speed,
        m_dot=core_mass_flow,
        gas=gas,
    )
    state0.total_air_mass_flow = config.mass_flow_rate
    state0.bypass_air_mass_flow = max(0.0, config.mass_flow_rate - core_mass_flow)
    state0.stage_name = "Freestream"
    return state0


def run_engine_case(config: EngineConfig | Mapping[str, Any] | None = None) -> EngineRunResult:
    runtime_config = prepare_config(config)
    gas = build_gas_from_config(runtime_config)
    engine = build_engine(runtime_config, gas)
    initial_state = build_initial_state(runtime_config, gas)
    return engine.run(initial_state, verbose=runtime_config.verbose)


def sweep_parameter(base_config: EngineConfig | Mapping[str, Any], parameter_name: str, values: list[float]) -> pd.DataFrame:
    rows = []
    config = prepare_config(base_config)
    for value in values:
        case_config = config.updated(**{parameter_name: float(value), "verbose": False})
        result = run_engine_case(case_config)
        summary = summarize_result(result, V0=case_config.flight_speed)
        rows.append(
            {
                parameter_name: float(value),
                "thrust_N": summary["thrust_N"],
                "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                "fuel_air_ratio": summary["fuel_air_ratio"],
                "tsfc_kg_per_N_s": summary["tsfc_kg_per_N_s"],
                "overall_efficiency": summary["overall_efficiency"],
                "exit_velocity_mps": summary["exit_velocity_mps"],
                "feasible": summary["feasible"],
            }
        )
    return pd.DataFrame(rows)


def sweep_compressor_pressure_ratio(base_config, pressure_ratios):
    return sweep_parameter(base_config, "compressor_pressure_ratio", list(pressure_ratios))


def sweep_flight_envelope(base_config, altitudes_m, flight_values, input_mode: str = "speed"):
    rows = []
    base = prepare_config(base_config)

    for altitude_m in altitudes_m:
        atmosphere = isa_atmosphere(float(altitude_m))
        for flight_value in flight_values:
            overrides: dict[str, Any] = {
                "altitude_m": float(altitude_m),
                "ambient_temperature": atmosphere.temperature,
                "ambient_pressure": atmosphere.pressure,
                "verbose": False,
            }
            if input_mode == "mach":
                overrides["flight_input_mode"] = "mach"
                overrides["flight_mach_number"] = float(flight_value)
            else:
                overrides["flight_input_mode"] = "speed"
                overrides["flight_speed"] = float(flight_value)
            case_config = base.updated(**overrides)
            result = run_engine_case(case_config)
            summary = summarize_result(result, V0=case_config.flight_speed)
            rows.append(
                {
                    "altitude_m": float(altitude_m),
                    "flight_input_mode": input_mode,
                    "flight_value": float(flight_value),
                    "flight_speed_mps": case_config.flight_speed,
                    "mach_number": case_config.flight_mach_number if input_mode == "mach" else (
                        case_config.flight_speed / max(speed_of_sound(atmosphere.temperature, build_gas_from_config(case_config)), 1e-9)
                    ),
                    "thrust_N": summary["thrust_N"],
                    "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                    "tsfc_kg_per_N_s": summary["tsfc_kg_per_N_s"],
                    "overall_efficiency": summary["overall_efficiency"],
                    "jet_power_efficiency": summary["jet_power_efficiency"],
                    "nozzle_choked": summary["nozzle_choked"],
                    "feasible": summary["feasible"],
                }
            )
    return pd.DataFrame(rows)
