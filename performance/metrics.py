from __future__ import annotations

from performance.efficiency import (
    jet_power_efficiency,
    overall_efficiency,
    propulsive_efficiency,
    shaft_efficiency,
    specific_impulse,
    thermal_efficiency,
    tsfc,
)
from performance.sizing import capture_area, equivalent_diameter
from performance.thrust import compute_thrust


def compute_bwr(state) -> float:
    if state.Wt == 0:
        return 0.0
    return state.Wc / state.Wt


def specific_work(state) -> float:
    return state.Wt - state.Wc


def specific_thrust(state, V0: float) -> float:
    total_air_mass_flow = getattr(state, "total_air_mass_flow", state.m_dot)
    if total_air_mass_flow <= 0:
        return 0.0
    return compute_thrust(state, V0) / total_air_mass_flow


def _stream_thrusts(state, V0: float) -> tuple[float, float]:
    core_air = state.m_dot
    bypass_air = getattr(state, "bypass_air_mass_flow", 0.0)
    core_exit_mass = core_air * (1.0 + state.fuel_air_ratio)
    core_thrust = core_exit_mass * state.V - core_air * V0 + state.pressure_thrust
    bypass_thrust = bypass_air * getattr(state, "bypass_exit_velocity", 0.0) - bypass_air * V0 + getattr(
        state, "bypass_pressure_thrust", 0.0
    )
    return core_thrust, bypass_thrust


def summarize_result(result, V0: float):
    final_state = result.final_state if hasattr(result, "final_state") else result[-1]
    initial_state = result[0] if hasattr(result, "__getitem__") else None
    total_air_mass_flow = getattr(final_state, "total_air_mass_flow", final_state.m_dot)
    fuel_flow = total_air_mass_flow * final_state.fuel_air_ratio
    core_thrust, bypass_thrust = _stream_thrusts(final_state, V0)
    inlet_capture = (
        capture_area(total_air_mass_flow, initial_state.rho, V0) if initial_state is not None and V0 > 0.0 else 0.0
    )

    return {
        "architecture": result.config.get("architecture", "turbojet") if hasattr(result, "config") else "turbojet",
        "preset_name": result.config.get("preset_name", "Custom") if hasattr(result, "config") else "Custom",
        "thrust_N": compute_thrust(final_state, V0),
        "core_thrust_N": core_thrust,
        "bypass_thrust_N": bypass_thrust,
        "specific_thrust_N_per_kg_s": specific_thrust(final_state, V0),
        "fuel_air_ratio": final_state.fuel_air_ratio,
        "fuel_flow_kg_s": fuel_flow,
        "tsfc_kg_per_N_s": tsfc(final_state, V0),
        "specific_impulse_s": specific_impulse(final_state, V0),
        "compressor_work_J_per_kg": final_state.Wc,
        "turbine_work_J_per_kg": final_state.Wt,
        "heat_input_J_per_kg": final_state.Qin,
        "bwr": compute_bwr(final_state),
        "shaft_efficiency": shaft_efficiency(final_state),
        "thermal_efficiency": thermal_efficiency(final_state, V0),
        "jet_power_efficiency": jet_power_efficiency(final_state, V0),
        "propulsive_efficiency": propulsive_efficiency(final_state, V0),
        "overall_efficiency": overall_efficiency(final_state, V0),
        "exit_velocity_mps": final_state.V,
        "exit_mach": final_state.M,
        "exit_static_temperature_K": final_state.T,
        "exit_total_temperature_K": final_state.Tt,
        "exit_static_pressure_Pa": final_state.P,
        "exit_total_pressure_Pa": final_state.Pt,
        "exit_area_m2": final_state.exit_area,
        "throat_area_m2": final_state.throat_area,
        "pressure_thrust_N": final_state.pressure_thrust,
        "nozzle_choked": final_state.nozzle_choked,
        "bypass_exit_velocity_mps": getattr(final_state, "bypass_exit_velocity", 0.0),
        "bypass_exit_mach": getattr(final_state, "bypass_exit_mach", 0.0),
        "bypass_exit_area_m2": getattr(final_state, "bypass_exit_area", 0.0),
        "bypass_throat_area_m2": getattr(final_state, "bypass_throat_area", 0.0),
        "bypass_nozzle_choked": getattr(final_state, "bypass_nozzle_choked", False),
        "total_air_mass_flow_kg_s": total_air_mass_flow,
        "core_air_mass_flow_kg_s": final_state.m_dot,
        "bypass_air_mass_flow_kg_s": getattr(final_state, "bypass_air_mass_flow", 0.0),
        "inlet_capture_area_m2": inlet_capture,
        "inlet_capture_diameter_m": equivalent_diameter(inlet_capture),
        "core_nozzle_diameter_m": equivalent_diameter(final_state.exit_area),
        "bypass_nozzle_diameter_m": equivalent_diameter(getattr(final_state, "bypass_exit_area", 0.0)),
        "feasible": not final_state.infeasible,
        "warnings": list(final_state.warnings),
    }
