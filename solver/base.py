from dataclasses import dataclass

import pandas as pd

from models.gas import STANDARD_AIR
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
    infeasible: bool
    status_message: str


class FlowState:
    def __init__(
        self,
        T,
        P,
        V=0.0,
        m_dot=1.0,
        Wc=0.0,
        Wt=0.0,
        Qin=0.0,
        gas=None,
    ):
        self.gas = gas or STANDARD_AIR
        self.cp = self.gas.cp
        self.gamma = self.gas.gamma
        self.R = self.gas.R

        self.T = T
        self.P = P
        self.V = V
        self.m_dot = m_dot

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
        self.fuel_air_ratio = 0.0
        self.pressure_thrust = 0.0
        self.exit_area = 0.0
        self.throat_area = 0.0
        self.nozzle_choked = False
        self.infeasible = False
        self.warnings = []

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
        self.fuel_air_ratio_ideal = 0.0
        self.pressure_thrust_ideal = 0.0
        self.exit_area_ideal = 0.0
        self.throat_area_ideal = 0.0
        self.nozzle_choked_ideal = False

        self.stage_name = ""
        self.stage_index = -1

        self.update_derived()

    def copy(self):
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
        new.s = self.s
        new.v = self.v
        new.rho = self.rho
        new.M = self.M
        new.area = self.area
        new.Tt = self.Tt
        new.Pt = self.Pt
        new.fuel_air_ratio = self.fuel_air_ratio
        new.pressure_thrust = self.pressure_thrust
        new.exit_area = self.exit_area
        new.throat_area = self.throat_area
        new.nozzle_choked = self.nozzle_choked
        new.infeasible = self.infeasible
        new.warnings = list(self.warnings)

        new.T_ideal = self.T_ideal
        new.P_ideal = self.P_ideal
        new.V_ideal = self.V_ideal
        new.s_ideal = self.s_ideal
        new.v_ideal = self.v_ideal
        new.rho_ideal = self.rho_ideal
        new.M_ideal = self.M_ideal
        new.area_ideal = self.area_ideal
        new.Tt_ideal = self.Tt_ideal
        new.Pt_ideal = self.Pt_ideal
        new.Wc_ideal = self.Wc_ideal
        new.Wt_ideal = self.Wt_ideal
        new.Qin_ideal = self.Qin_ideal
        new.fuel_air_ratio_ideal = self.fuel_air_ratio_ideal
        new.pressure_thrust_ideal = self.pressure_thrust_ideal
        new.exit_area_ideal = self.exit_area_ideal
        new.throat_area_ideal = self.throat_area_ideal
        new.nozzle_choked_ideal = self.nozzle_choked_ideal

        new.stage_name = self.stage_name
        new.stage_index = self.stage_index
        return new

    @property
    def status_message(self):
        return " | ".join(self.warnings)

    @property
    def m_dot_actual(self):
        return self.m_dot * (1.0 + self.fuel_air_ratio)

    @property
    def m_dot_ideal(self):
        return self.m_dot * (1.0 + self.fuel_air_ratio_ideal)

    def set_actual_static(self, temperature, pressure, velocity):
        self.T = temperature
        self.P = pressure
        self.V = velocity

    def set_actual_total(self, temperature_total, pressure_total, velocity):
        static_state = static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, self.gas)
        self.T = static_state["temperature"]
        self.P = static_state["pressure"]
        self.V = velocity
        self.Tt = temperature_total
        self.Pt = pressure_total

    def set_ideal_static(self, temperature, pressure, velocity):
        self.T_ideal = temperature
        self.P_ideal = pressure
        self.V_ideal = velocity

    def set_ideal_total(self, temperature_total, pressure_total, velocity):
        static_state = static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, self.gas)
        self.T_ideal = static_state["temperature"]
        self.P_ideal = static_state["pressure"]
        self.V_ideal = velocity
        self.Tt_ideal = temperature_total
        self.Pt_ideal = pressure_total

    def add_warning(self, message):
        if message and message not in self.warnings:
            self.warnings.append(message)

    def mark_infeasible(self, message):
        self.infeasible = True
        self.add_warning(message)

    def update_derived(self):
        self.v = specific_volume(self.T, self.P, self.R)
        self.rho = density(self.T, self.P, self.R)
        self.M = mach_number(self.V, self.T, self.gamma, self.R)
        stagnation_actual = stagnation_state_from_static(self.T, self.P, self.V, self.gas)
        self.Tt = stagnation_actual["temperature"]
        self.Pt = stagnation_actual["pressure"]
        self.area = flow_area(self.m_dot_actual, self.rho, self.V) if self.V > 1e-9 else 0.0

        self.v_ideal = specific_volume(self.T_ideal, self.P_ideal, self.R)
        self.rho_ideal = density(self.T_ideal, self.P_ideal, self.R)
        self.M_ideal = mach_number(self.V_ideal, self.T_ideal, self.gamma, self.R)
        stagnation_ideal = stagnation_state_from_static(self.T_ideal, self.P_ideal, self.V_ideal, self.gas)
        self.Tt_ideal = stagnation_ideal["temperature"]
        self.Pt_ideal = stagnation_ideal["pressure"]
        self.area_ideal = flow_area(self.m_dot_ideal, self.rho_ideal, self.V_ideal) if self.V_ideal > 1e-9 else 0.0

    def to_station_record(self):
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
            infeasible=self.infeasible,
            status_message=self.status_message,
        )


class EngineRunResult:
    def __init__(self, states, gas, config):
        self.states = states
        self.gas = gas
        self.config = config

    def __iter__(self):
        return iter(self.states)

    def __getitem__(self, item):
        return self.states[item]

    def __len__(self):
        return len(self.states)

    @property
    def final_state(self):
        return self.states[-1]

    @property
    def feasible(self):
        return not self.final_state.infeasible

    @property
    def warnings(self):
        return list(self.final_state.warnings)

    @property
    def station_records(self):
        return [state.to_station_record() for state in self.states]

    def to_dataframe(self):
        frame = pd.DataFrame([record.__dict__ for record in self.station_records])
        frame["fuel_air_ratio"] = frame["cumulative_fuel_air_ratio"]
        frame["actual_temperature_K"] = frame["actual_static_temperature_K"]
        frame["actual_pressure_kPa"] = frame["actual_static_pressure_kPa"]
        frame["ideal_temperature_K"] = frame["ideal_static_temperature_K"]
        frame["ideal_pressure_kPa"] = frame["ideal_static_pressure_kPa"]
        return frame

    def to_component_dataframe(self):
        rows = []

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
    def __init__(self, name="Stage"):
        self.name = name

    def process(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Subclasses must implement the process method.")
