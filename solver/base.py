from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from models.gas import IdealGas, STANDARD_AIR
from solver.cycle import (
    density,
    flow_area,
    mach_number,
    specific_volume,
    stagnation_state_from_static,
    static_state_from_total_and_velocity,
)


@dataclass
class StationRecord:
    stage_name: str
    stage_index: int
    actual_static_temperature_K: float
    actual_total_temperature_K: float
    actual_static_pressure_kPa: float
    actual_total_pressure_kPa: float
    actual_velocity_mps: float
    actual_entropy_J_per_kgK: float
    actual_specific_volume_m3_per_kg: float
    actual_density_kg_per_m3: float
    actual_mach: float
    actual_area_m2: float
    ideal_static_temperature_K: float
    ideal_total_temperature_K: float
    ideal_static_pressure_kPa: float
    ideal_total_pressure_kPa: float
    ideal_velocity_mps: float
    ideal_entropy_J_per_kgK: float
    ideal_specific_volume_m3_per_kg: float
    ideal_density_kg_per_m3: float
    ideal_mach: float
    ideal_area_m2: float
    cumulative_fuel_air_ratio: float
    heat_input_J_per_kg_air: float
    compressor_work_J_per_kg_air: float
    turbine_work_J_per_kg_air: float
    pressure_thrust_N: float
    nozzle_choked: bool
    core_air_mass_flow_kg_s: float
    bypass_air_mass_flow_kg_s: float
    total_air_mass_flow_kg_s: float
    bypass_pressure_thrust_N: float
    infeasible: bool
    status_message: str


class FlowState:
    def __init__(
        self,
        T: float,
        P: float,
        V: float = 0.0,
        m_dot: float = 1.0,
        Wc: float = 0.0,
        Wt: float = 0.0,
        Qin: float = 0.0,
        gas: IdealGas | None = None,
    ) -> None:
        self.gas = gas or STANDARD_AIR
        self.cp = self.gas.cp_at(T)
        self.gamma = self.gas.gamma_at(T)
        self.R = self.gas.R

        self.T = T
        self.P = P
        self.V = V
        self.m_dot = m_dot
        self.total_air_mass_flow = m_dot
        self.bypass_air_mass_flow = 0.0

        self.s = 0.0
        self.v = 0.0
        self.rho = 0.0
        self.M = 0.0
        self.area = 0.0
        self.Tt = T
        self.Pt = P
        self.Wc = Wc
        self.Wt = Wt
        self.Qin = Qin
        self.work_breakdown: dict[str, float] = {}
        self.fuel_air_ratio = 0.0
        self.pressure_thrust = 0.0
        self.exit_area = 0.0
        self.throat_area = 0.0
        self.nozzle_choked = False
        self.bypass_exit_velocity = 0.0
        self.bypass_exit_mach = 0.0
        self.bypass_exit_area = 0.0
        self.bypass_throat_area = 0.0
        self.bypass_pressure_thrust = 0.0
        self.bypass_nozzle_choked = False
        self.infeasible = False
        self.warnings: list[str] = []

        self.T_ideal = T
        self.P_ideal = P
        self.V_ideal = V
        self.s_ideal = 0.0
        self.v_ideal = 0.0
        self.rho_ideal = 0.0
        self.M_ideal = 0.0
        self.area_ideal = 0.0
        self.Tt_ideal = T
        self.Pt_ideal = P
        self.Wc_ideal = Wc
        self.Wt_ideal = Wt
        self.Qin_ideal = Qin
        self.work_breakdown_ideal: dict[str, float] = {}
        self.fuel_air_ratio_ideal = 0.0
        self.pressure_thrust_ideal = 0.0
        self.exit_area_ideal = 0.0
        self.throat_area_ideal = 0.0
        self.nozzle_choked_ideal = False

        self.stage_name = ""
        self.stage_index = -1
        self.update_derived()

    def copy(self) -> "FlowState":
        new = FlowState(
            self.T,
            self.P,
            self.V,
            self.m_dot,
            self.Wc,
            self.Wt,
            self.Qin,
            self.gas,
        )
        for name in (
            "s",
            "v",
            "rho",
            "M",
            "area",
            "Tt",
            "Pt",
            "fuel_air_ratio",
            "pressure_thrust",
            "exit_area",
            "throat_area",
            "nozzle_choked",
            "bypass_exit_velocity",
            "bypass_exit_mach",
            "bypass_exit_area",
            "bypass_throat_area",
            "bypass_pressure_thrust",
            "bypass_nozzle_choked",
            "infeasible",
            "total_air_mass_flow",
            "bypass_air_mass_flow",
        ):
            setattr(new, name, getattr(self, name))
        new.warnings = list(self.warnings)
        new.work_breakdown = dict(self.work_breakdown)

        for name in (
            "T_ideal",
            "P_ideal",
            "V_ideal",
            "s_ideal",
            "v_ideal",
            "rho_ideal",
            "M_ideal",
            "area_ideal",
            "Tt_ideal",
            "Pt_ideal",
            "Wc_ideal",
            "Wt_ideal",
            "Qin_ideal",
            "fuel_air_ratio_ideal",
            "pressure_thrust_ideal",
            "exit_area_ideal",
            "throat_area_ideal",
            "nozzle_choked_ideal",
        ):
            setattr(new, name, getattr(self, name))
        new.work_breakdown_ideal = dict(self.work_breakdown_ideal)
        new.stage_name = self.stage_name
        new.stage_index = self.stage_index
        return new

    @property
    def status_message(self) -> str:
        return " | ".join(self.warnings)

    @property
    def m_dot_actual(self) -> float:
        return self.m_dot * (1.0 + self.fuel_air_ratio)

    @property
    def m_dot_ideal(self) -> float:
        return self.m_dot * (1.0 + self.fuel_air_ratio_ideal)

    @property
    def core_air_mass_flow(self) -> float:
        return self.m_dot

    def set_actual_static(self, temperature: float, pressure: float, velocity: float) -> None:
        self.T = temperature
        self.P = pressure
        self.V = velocity

    def set_actual_total(self, temperature_total: float, pressure_total: float, velocity: float) -> None:
        static_state = static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, self.gas)
        self.T = static_state["temperature"]
        self.P = static_state["pressure"]
        self.V = velocity
        self.Tt = temperature_total
        self.Pt = pressure_total

    def set_ideal_static(self, temperature: float, pressure: float, velocity: float) -> None:
        self.T_ideal = temperature
        self.P_ideal = pressure
        self.V_ideal = velocity

    def set_ideal_total(self, temperature_total: float, pressure_total: float, velocity: float) -> None:
        static_state = static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, self.gas)
        self.T_ideal = static_state["temperature"]
        self.P_ideal = static_state["pressure"]
        self.V_ideal = velocity
        self.Tt_ideal = temperature_total
        self.Pt_ideal = pressure_total

    def add_work(self, key: str, value: float, ideal: bool = False) -> None:
        target = self.work_breakdown_ideal if ideal else self.work_breakdown
        target[key] = target.get(key, 0.0) + value

    def get_work(self, key: str, ideal: bool = False) -> float:
        source = self.work_breakdown_ideal if ideal else self.work_breakdown
        return source.get(key, 0.0)

    def add_warning(self, message: str) -> None:
        if message and message not in self.warnings:
            self.warnings.append(message)

    def mark_infeasible(self, message: str) -> None:
        self.infeasible = True
        self.add_warning(message)

    def update_derived(self) -> None:
        self.cp = self.gas.cp_at(self.T)
        self.gamma = self.gas.gamma_at(self.T)
        self.v = specific_volume(self.T, self.P, self.R)
        self.rho = density(self.T, self.P, self.R)
        self.M = mach_number(self.V, self.T, self.gas)
        stagnation_actual = stagnation_state_from_static(self.T, self.P, self.V, self.gas)
        self.Tt = stagnation_actual["temperature"]
        self.Pt = stagnation_actual["pressure"]
        self.area = flow_area(self.m_dot_actual, self.rho, self.V) if self.V > 1e-9 else 0.0

        self.v_ideal = specific_volume(self.T_ideal, self.P_ideal, self.R)
        self.rho_ideal = density(self.T_ideal, self.P_ideal, self.R)
        self.M_ideal = mach_number(self.V_ideal, self.T_ideal, self.gas)
        stagnation_ideal = stagnation_state_from_static(self.T_ideal, self.P_ideal, self.V_ideal, self.gas)
        self.Tt_ideal = stagnation_ideal["temperature"]
        self.Pt_ideal = stagnation_ideal["pressure"]
        self.area_ideal = flow_area(self.m_dot_ideal, self.rho_ideal, self.V_ideal) if self.V_ideal > 1e-9 else 0.0

    def to_station_record(self) -> StationRecord:
        return StationRecord(
            stage_name=self.stage_name or "Freestream",
            stage_index=self.stage_index,
            actual_static_temperature_K=self.T,
            actual_total_temperature_K=self.Tt,
            actual_static_pressure_kPa=self.P / 1000.0,
            actual_total_pressure_kPa=self.Pt / 1000.0,
            actual_velocity_mps=self.V,
            actual_entropy_J_per_kgK=self.s,
            actual_specific_volume_m3_per_kg=self.v,
            actual_density_kg_per_m3=self.rho,
            actual_mach=self.M,
            actual_area_m2=self.area,
            ideal_static_temperature_K=self.T_ideal,
            ideal_total_temperature_K=self.Tt_ideal,
            ideal_static_pressure_kPa=self.P_ideal / 1000.0,
            ideal_total_pressure_kPa=self.Pt_ideal / 1000.0,
            ideal_velocity_mps=self.V_ideal,
            ideal_entropy_J_per_kgK=self.s_ideal,
            ideal_specific_volume_m3_per_kg=self.v_ideal,
            ideal_density_kg_per_m3=self.rho_ideal,
            ideal_mach=self.M_ideal,
            ideal_area_m2=self.area_ideal,
            cumulative_fuel_air_ratio=self.fuel_air_ratio,
            heat_input_J_per_kg_air=self.Qin,
            compressor_work_J_per_kg_air=self.Wc,
            turbine_work_J_per_kg_air=self.Wt,
            pressure_thrust_N=self.pressure_thrust,
            nozzle_choked=self.nozzle_choked,
            core_air_mass_flow_kg_s=self.m_dot,
            bypass_air_mass_flow_kg_s=self.bypass_air_mass_flow,
            total_air_mass_flow_kg_s=self.total_air_mass_flow,
            bypass_pressure_thrust_N=self.bypass_pressure_thrust,
            infeasible=self.infeasible,
            status_message=self.status_message,
        )


class EngineRunResult:
    def __init__(
        self,
        states: list[FlowState],
        gas: IdealGas,
        config: dict[str, Any],
        extras: dict[str, Any] | None = None,
        assumptions: list[str] | None = None,
        equations: list[str] | None = None,
    ) -> None:
        self.states = states
        self.gas = gas
        self.config = config
        self.extras = extras or {}
        self.assumptions = assumptions or []
        self.equations = equations or []

    def __iter__(self):
        return iter(self.states)

    def __getitem__(self, item):
        return self.states[item]

    def __len__(self):
        return len(self.states)

    @property
    def final_state(self) -> FlowState:
        return self.states[-1]

    @property
    def feasible(self) -> bool:
        return not self.final_state.infeasible

    @property
    def warnings(self) -> list[str]:
        return list(self.final_state.warnings)

    @property
    def station_records(self) -> list[StationRecord]:
        return [state.to_station_record() for state in self.states]

    def to_dataframe(self) -> pd.DataFrame:
        frame = pd.DataFrame([record.__dict__ for record in self.station_records])
        frame["fuel_air_ratio"] = frame["cumulative_fuel_air_ratio"]
        frame["actual_temperature_K"] = frame["actual_static_temperature_K"]
        frame["actual_pressure_kPa"] = frame["actual_static_pressure_kPa"]
        frame["ideal_temperature_K"] = frame["ideal_static_temperature_K"]
        frame["ideal_pressure_kPa"] = frame["ideal_static_pressure_kPa"]
        return frame

    def to_component_dataframe(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for index in range(1, len(self.states)):
            inlet = self.states[index - 1]
            outlet = self.states[index]
            rows.append(
                {
                    "stage_name": outlet.stage_name or f"Stage {index}",
                    "actual_delta_static_temperature_K": outlet.T - inlet.T,
                    "actual_delta_total_temperature_K": outlet.Tt - inlet.Tt,
                    "actual_static_pressure_ratio": outlet.P / inlet.P if inlet.P else 0.0,
                    "actual_total_pressure_ratio": outlet.Pt / inlet.Pt if inlet.Pt else 0.0,
                    "actual_delta_velocity_mps": outlet.V - inlet.V,
                    "actual_area_ratio": outlet.area / inlet.area if inlet.area > 0 else 0.0,
                    "ideal_delta_static_temperature_K": outlet.T_ideal - inlet.T_ideal,
                    "ideal_delta_total_temperature_K": outlet.Tt_ideal - inlet.Tt_ideal,
                    "ideal_static_pressure_ratio": outlet.P_ideal / inlet.P_ideal if inlet.P_ideal else 0.0,
                    "ideal_total_pressure_ratio": outlet.Pt_ideal / inlet.Pt_ideal if inlet.Pt_ideal else 0.0,
                    "ideal_delta_velocity_mps": outlet.V_ideal - inlet.V_ideal,
                    "ideal_area_ratio": outlet.area_ideal / inlet.area_ideal if inlet.area_ideal > 0 else 0.0,
                    "delta_heat_input_J_per_kg_air": outlet.Qin - inlet.Qin,
                    "delta_compressor_work_J_per_kg_air": outlet.Wc - inlet.Wc,
                    "delta_turbine_work_J_per_kg_air": outlet.Wt - inlet.Wt,
                }
            )
        return pd.DataFrame(rows)


class Stage:
    def __init__(self, name: str = "Stage") -> None:
        self.name = name

    def process(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Subclasses must implement the process method.")
