from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from configs.default import (
    EngineConfig,
    get_default_engine_config,
)
from models.atmosphere import isa_atmosphere
from models.gas import IdealGas, build_gas_from_config
from performance.metrics import summarize_result
from solver.base import EngineRunResult, FlowState
from solver.cycle import entropy_change, nozzle_exit_state, speed_of_sound


ENGINE_ASSUMPTIONS = [
    "The cycle is modeled as a one-dimensional, steady-flow Brayton cycle.",
    "Air is treated as an ideal gas with constant specific heats.",
    "The compressor and turbine are adiabatic with isentropic efficiencies.",
    "Combustion is represented by heat addition to a target turbine inlet temperature with a pressure loss.",
    "The nozzle is a simple convergent nozzle expanding to ambient or choked conditions.",
]

ENGINE_EQUATIONS = [
    r"T_t = T + \frac{V^2}{2 c_p}",
    r"\frac{P_t}{P} = \left(\frac{T_t}{T}\right)^{\frac{\gamma}{\gamma - 1}}",
    r"\eta_c = \frac{T_{t,2s} - T_{t,1}}{T_{t,2} - T_{t,1}}",
    r"\eta_t = \frac{T_{t,3} - T_{t,4}}{T_{t,3} - T_{t,4s}}",
    r"f = \frac{c_p (T_{t,3} - T_{t,2})}{\eta_b \, LHV}",
    r"F = \dot{m}_a \left[(1 + f)V_e - V_0\right] + (P_e - P_0)A_e",
]


def _coerce_config(config: EngineConfig | Mapping[str, Any] | None) -> EngineConfig:
    if isinstance(config, EngineConfig):
        return config

    return get_default_engine_config().updated(**dict(config or {}))


def _resolve_ambient_conditions(config: EngineConfig) -> EngineConfig:
    atmosphere = isa_atmosphere(config.altitude_m)
    ambient_temperature = config.ambient_temperature if config.ambient_temperature is not None else atmosphere.temperature
    ambient_pressure = config.ambient_pressure if config.ambient_pressure is not None else atmosphere.pressure

    resolved = config.updated(
        ambient_temperature=ambient_temperature,
        ambient_pressure=ambient_pressure,
    )
    if resolved.flight_input_mode == "mach":
        gas = build_gas_from_config(resolved)
        flight_speed = resolved.flight_mach_number * speed_of_sound(ambient_temperature, gas)
        resolved = resolved.updated(flight_speed=flight_speed)
    return resolved


def validate_config(config: EngineConfig) -> None:
    if config.flight_input_mode not in {"speed", "mach"}:
        raise ValueError("flight_input_mode must be either 'speed' or 'mach'.")
    if config.altitude_m < 0.0:
        raise ValueError("altitude_m must be non-negative.")
    if config.flight_speed < 0.0 or config.flight_mach_number < 0.0:
        raise ValueError("flight speed and Mach number must be non-negative.")
    if config.mass_flow_rate <= 0.0:
        raise ValueError("mass_flow_rate must be greater than zero.")
    if config.pressure_recovery <= 0.0 or config.pressure_recovery > 1.0:
        raise ValueError("pressure_recovery must be between 0 and 1.")
    if config.compressor_pressure_ratio < 1.0:
        raise ValueError("compressor_pressure_ratio must be at least 1.")
    for value, label in (
        (config.compressor_efficiency, "compressor_efficiency"),
        (config.combustor_efficiency, "combustor_efficiency"),
        (config.turbine_efficiency, "turbine_efficiency"),
        (config.mechanical_efficiency, "mechanical_efficiency"),
        (config.nozzle_efficiency, "nozzle_efficiency"),
    ):
        if value <= 0.0 or value > 1.0:
            raise ValueError(f"{label} must be greater than 0 and at most 1.")
    if config.combustor_pressure_loss < 0.0 or config.combustor_pressure_loss >= 1.0:
        raise ValueError("combustor_pressure_loss must be between 0 and 1.")
    if config.turbine_inlet_temperature <= 0.0:
        raise ValueError("turbine_inlet_temperature must be positive.")
    if config.gas_cp <= 0.0 or config.gas_gamma <= 1.0:
        raise ValueError("gas properties are invalid.")
    if config.gas_R is not None and config.gas_R <= 0.0:
        raise ValueError("gas_R must be positive when provided.")
    if config.fuel_lower_heating_value <= 0.0:
        raise ValueError("fuel_lower_heating_value must be positive.")
    if (config.ambient_temperature or 1.0) <= 0.0 or (config.ambient_pressure or 1.0) <= 0.0:
        raise ValueError("ambient conditions must be positive.")


def prepare_config(config: EngineConfig | Mapping[str, Any] | None = None) -> EngineConfig:
    resolved = _resolve_ambient_conditions(_coerce_config(config))
    validate_config(resolved)
    return resolved


def build_initial_state(config: EngineConfig, gas: IdealGas) -> FlowState:
    state = FlowState(
        T=config.ambient_temperature if config.ambient_temperature is not None else 288.15,
        P=config.ambient_pressure if config.ambient_pressure is not None else 101325.0,
        V=config.flight_speed,
        m_dot=config.mass_flow_rate,
        gas=gas,
    )
    state.stage_name = "Freestream"
    return state


def _append_total_state(
    states: list[FlowState],
    stage_name: str,
    actual_total_temperature: float,
    actual_total_pressure: float,
    actual_velocity: float,
    ideal_total_temperature: float,
    ideal_total_pressure: float,
    ideal_velocity: float,
) -> FlowState:
    previous = states[-1]
    state = previous.copy()
    state.set_actual_total(actual_total_temperature, actual_total_pressure, actual_velocity)
    state.set_ideal_total(ideal_total_temperature, ideal_total_pressure, ideal_velocity)
    state.stage_name = stage_name
    state.stage_index = len(states) - 1
    state.s = previous.s + entropy_change(state.T, previous.T, state.P, previous.P, state.gas)
    state.s_ideal = previous.s_ideal + entropy_change(
        state.T_ideal,
        previous.T_ideal,
        state.P_ideal,
        previous.P_ideal,
        state.gas,
    )
    state.update_derived()
    states.append(state)
    return state


def _append_nozzle_state(
    states: list[FlowState],
    actual_nozzle: dict[str, float | bool | str],
    ideal_nozzle: dict[str, float | bool | str],
) -> FlowState:
    previous = states[-1]
    state = previous.copy()
    state.set_actual_static(
        float(actual_nozzle["temperature"]),
        float(actual_nozzle["pressure"]),
        float(actual_nozzle["velocity"]),
    )
    state.set_ideal_static(
        float(ideal_nozzle["temperature"]),
        float(ideal_nozzle["pressure"]),
        float(ideal_nozzle["velocity"]),
    )
    state.stage_name = "Nozzle"
    state.stage_index = len(states) - 1
    state.pressure_thrust = float(actual_nozzle["pressure_thrust"])
    state.pressure_thrust_ideal = float(ideal_nozzle["pressure_thrust"])
    state.exit_area = float(actual_nozzle["exit_area"])
    state.exit_area_ideal = float(ideal_nozzle["exit_area"])
    state.throat_area = float(actual_nozzle["throat_area"])
    state.throat_area_ideal = float(ideal_nozzle["throat_area"])
    state.nozzle_choked = bool(actual_nozzle["choked"])
    state.nozzle_choked_ideal = bool(ideal_nozzle["choked"])
    state.s = previous.s + entropy_change(state.T, previous.T, state.P, previous.P, state.gas)
    state.s_ideal = previous.s_ideal + entropy_change(
        state.T_ideal,
        previous.T_ideal,
        state.P_ideal,
        previous.P_ideal,
        state.gas,
    )
    if not bool(actual_nozzle["feasible"]):
        state.mark_infeasible(str(actual_nozzle["message"]))
    state.update_derived()
    states.append(state)
    return state


def run_engine_case(config: EngineConfig | Mapping[str, Any] | None = None) -> EngineRunResult:
    runtime_config = prepare_config(config)
    gas = build_gas_from_config(runtime_config)
    cp = gas.cp
    states = [build_initial_state(runtime_config, gas)]

    station0 = states[0]
    Tt0 = station0.Tt
    Pt0 = station0.Pt

    inlet_state = _append_total_state(
        states,
        "Inlet",
        actual_total_temperature=Tt0,
        actual_total_pressure=Pt0 * runtime_config.pressure_recovery,
        actual_velocity=runtime_config.diffuser_exit_velocity,
        ideal_total_temperature=Tt0,
        ideal_total_pressure=Pt0,
        ideal_velocity=runtime_config.diffuser_exit_velocity,
    )

    Tt2s = inlet_state.Tt * runtime_config.compressor_pressure_ratio ** ((gas.gamma - 1.0) / gas.gamma)
    Tt2 = inlet_state.Tt + (Tt2s - inlet_state.Tt) / runtime_config.compressor_efficiency
    compressor_state = _append_total_state(
        states,
        "Compressor",
        actual_total_temperature=Tt2,
        actual_total_pressure=inlet_state.Pt * runtime_config.compressor_pressure_ratio,
        actual_velocity=runtime_config.compressor_exit_velocity,
        ideal_total_temperature=Tt2s,
        ideal_total_pressure=inlet_state.Pt_ideal * runtime_config.compressor_pressure_ratio,
        ideal_velocity=runtime_config.compressor_exit_velocity,
    )
    compressor_state.Wc = inlet_state.Wc + cp * (compressor_state.Tt - inlet_state.Tt)
    compressor_state.Wc_ideal = inlet_state.Wc_ideal + cp * (compressor_state.Tt_ideal - inlet_state.Tt_ideal)

    combustor_total_pressure = compressor_state.Pt * (1.0 - runtime_config.combustor_pressure_loss)
    combustor_state = _append_total_state(
        states,
        "Combustor",
        actual_total_temperature=runtime_config.turbine_inlet_temperature,
        actual_total_pressure=combustor_total_pressure,
        actual_velocity=runtime_config.combustor_exit_velocity,
        ideal_total_temperature=runtime_config.turbine_inlet_temperature,
        ideal_total_pressure=compressor_state.Pt_ideal,
        ideal_velocity=runtime_config.combustor_exit_velocity,
    )
    combustor_state.Wc = compressor_state.Wc
    combustor_state.Wc_ideal = compressor_state.Wc_ideal
    combustor_state.Qin = compressor_state.Qin + cp * (combustor_state.Tt - compressor_state.Tt)
    combustor_state.Qin_ideal = compressor_state.Qin_ideal + cp * (
        combustor_state.Tt_ideal - compressor_state.Tt_ideal
    )
    combustor_state.fuel_air_ratio = combustor_state.Qin / (
        runtime_config.combustor_efficiency * runtime_config.fuel_lower_heating_value
    )
    combustor_state.fuel_air_ratio_ideal = combustor_state.Qin_ideal / runtime_config.fuel_lower_heating_value

    required_turbine_work = (compressor_state.Wc - inlet_state.Wc) / runtime_config.mechanical_efficiency
    required_turbine_work_ideal = compressor_state.Wc_ideal - inlet_state.Wc_ideal
    delta_t_turbine = required_turbine_work / max(cp * (1.0 + combustor_state.fuel_air_ratio), 1e-9)
    delta_t_turbine_ideal = required_turbine_work_ideal / max(cp * (1.0 + combustor_state.fuel_air_ratio_ideal), 1e-9)
    Tt4 = combustor_state.Tt - delta_t_turbine
    Tt4_ideal = combustor_state.Tt_ideal - delta_t_turbine_ideal
    Tt4s = combustor_state.Tt - (combustor_state.Tt - Tt4) / runtime_config.turbine_efficiency
    Pt4 = combustor_state.Pt * (Tt4s / max(combustor_state.Tt, 1e-9)) ** (gas.gamma / (gas.gamma - 1.0))
    Pt4_ideal = combustor_state.Pt_ideal * (Tt4_ideal / max(combustor_state.Tt_ideal, 1e-9)) ** (
        gas.gamma / (gas.gamma - 1.0)
    )

    turbine_state = _append_total_state(
        states,
        "Turbine",
        actual_total_temperature=Tt4,
        actual_total_pressure=Pt4,
        actual_velocity=runtime_config.turbine_exit_velocity,
        ideal_total_temperature=Tt4_ideal,
        ideal_total_pressure=Pt4_ideal,
        ideal_velocity=runtime_config.turbine_exit_velocity,
    )
    turbine_state.Wc = combustor_state.Wc
    turbine_state.Wc_ideal = combustor_state.Wc_ideal
    turbine_state.Qin = combustor_state.Qin
    turbine_state.Qin_ideal = combustor_state.Qin_ideal
    turbine_state.fuel_air_ratio = combustor_state.fuel_air_ratio
    turbine_state.fuel_air_ratio_ideal = combustor_state.fuel_air_ratio_ideal
    turbine_state.Wt = combustor_state.Wt + required_turbine_work
    turbine_state.Wt_ideal = combustor_state.Wt_ideal + required_turbine_work_ideal

    actual_nozzle = nozzle_exit_state(
        turbine_state.Tt,
        turbine_state.Pt,
        runtime_config.ambient_pressure if runtime_config.ambient_pressure is not None else 101325.0,
        gas,
        runtime_config.nozzle_efficiency,
        turbine_state.m_dot_actual,
    )
    ideal_nozzle = nozzle_exit_state(
        turbine_state.Tt_ideal,
        turbine_state.Pt_ideal,
        runtime_config.ambient_pressure if runtime_config.ambient_pressure is not None else 101325.0,
        gas,
        1.0,
        turbine_state.m_dot * (1.0 + turbine_state.fuel_air_ratio_ideal),
    )
    nozzle_state = _append_nozzle_state(states, actual_nozzle, ideal_nozzle)
    nozzle_state.Wc = turbine_state.Wc
    nozzle_state.Wc_ideal = turbine_state.Wc_ideal
    nozzle_state.Wt = turbine_state.Wt
    nozzle_state.Wt_ideal = turbine_state.Wt_ideal
    nozzle_state.Qin = turbine_state.Qin
    nozzle_state.Qin_ideal = turbine_state.Qin_ideal
    nozzle_state.fuel_air_ratio = turbine_state.fuel_air_ratio
    nozzle_state.fuel_air_ratio_ideal = turbine_state.fuel_air_ratio_ideal

    if turbine_state.Tt <= runtime_config.ambient_temperature:
        nozzle_state.mark_infeasible("Turbine exit total temperature fell to ambient or below.")
    if turbine_state.Pt <= runtime_config.ambient_pressure:
        nozzle_state.add_warning("Turbine exit total pressure is close to ambient, so nozzle thrust is limited.")

    if runtime_config.verbose:
        for state in states[1:]:
            print(
                f"{state.stage_name}: "
                f"T = {state.T:.1f} K, P = {state.P / 1000.0:.1f} kPa, "
                f"Tt = {state.Tt:.1f} K, Pt = {state.Pt / 1000.0:.1f} kPa"
            )

    return EngineRunResult(
        states=states,
        gas=gas,
        config=runtime_config.to_dict(),
        assumptions=ENGINE_ASSUMPTIONS,
        equations=ENGINE_EQUATIONS,
    )


def sweep_parameter(
    base_config: EngineConfig | Mapping[str, Any],
    parameter_name: str,
    values: list[float],
) -> pd.DataFrame:
    """Run a one-at-a-time parameter study.

    Each value in ``values`` is solved as a fresh Brayton-cycle case while all
    non-swept inputs are kept at the current baseline configuration.

    Notes:
    - Sweeping ``altitude_m`` triggers a fresh ISA atmosphere evaluation inside
      ``run_engine_case``.
    - Sweeping ``flight_speed`` forces ``flight_input_mode='speed'`` so the
      sampled speed is not overwritten by Mach-based preprocessing.
    """
    rows = []
    config = prepare_config(base_config)
    for value in values:
        overrides: dict[str, Any] = {parameter_name: float(value), "verbose": False}
        if parameter_name == "flight_speed":
            overrides["flight_input_mode"] = "speed"
        case_config = config.updated(**overrides)
        result = run_engine_case(case_config)
        summary = summarize_result(result, V0=result.config["flight_speed"])
        rows.append(
            {
                parameter_name: float(value),
                "thrust_N": summary["thrust_N"],
                "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                "fuel_air_ratio": summary["fuel_air_ratio"],
                "fuel_flow_kg_s": summary["fuel_flow_kg_s"],
                "overall_efficiency": summary["overall_efficiency"],
                "thermal_efficiency": summary["thermal_efficiency"],
                "feasible": summary["feasible"],
            }
        )
    return pd.DataFrame(rows)


def sweep_compressor_pressure_ratio(base_config, pressure_ratios):
    return sweep_parameter(base_config, "compressor_pressure_ratio", list(pressure_ratios))
