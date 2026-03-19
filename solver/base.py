from dataclasses import dataclass

import pandas as pd

from models.gas import STANDARD_AIR
from solver.cycle import specific_volume


@dataclass
class StationRecord:
    stage_name: str
    stage_index: int
    actual_temperature_K: float
    actual_pressure_kPa: float
    actual_velocity_mps: float
    actual_entropy_J_per_kgK: float
    actual_specific_volume_m3_per_kg: float
    ideal_temperature_K: float
    ideal_pressure_kPa: float
    ideal_velocity_mps: float
    ideal_entropy_J_per_kgK: float
    ideal_specific_volume_m3_per_kg: float
    cumulative_fuel_air_ratio: float
    heat_input_J_per_kg_air: float
    compressor_work_J_per_kg_air: float
    turbine_work_J_per_kg_air: float
    nozzle_choked: bool


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
        self.Wc = Wc
        self.Wt = Wt
        self.Qin = Qin
        self.fuel_air_ratio = 0.0
        self.pressure_thrust = 0.0
        self.exit_area = 0.0
        self.nozzle_choked = False

        self.T_ideal = T
        self.P_ideal = P
        self.V_ideal = V
        self.s_ideal = 0.0
        self.v_ideal = 0.0
        self.Wc_ideal = Wc
        self.Wt_ideal = Wt
        self.Qin_ideal = Qin
        self.fuel_air_ratio_ideal = 0.0
        self.pressure_thrust_ideal = 0.0
        self.exit_area_ideal = 0.0
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
        new.fuel_air_ratio = self.fuel_air_ratio
        new.pressure_thrust = self.pressure_thrust
        new.exit_area = self.exit_area
        new.nozzle_choked = self.nozzle_choked

        new.T_ideal = self.T_ideal
        new.P_ideal = self.P_ideal
        new.V_ideal = self.V_ideal
        new.s_ideal = self.s_ideal
        new.v_ideal = self.v_ideal
        new.Wc_ideal = self.Wc_ideal
        new.Wt_ideal = self.Wt_ideal
        new.Qin_ideal = self.Qin_ideal
        new.fuel_air_ratio_ideal = self.fuel_air_ratio_ideal
        new.pressure_thrust_ideal = self.pressure_thrust_ideal
        new.exit_area_ideal = self.exit_area_ideal
        new.nozzle_choked_ideal = self.nozzle_choked_ideal

        new.stage_name = self.stage_name
        new.stage_index = self.stage_index
        return new

    def update_derived(self):
        self.v = specific_volume(self.T, self.P, self.R)
        self.v_ideal = specific_volume(self.T_ideal, self.P_ideal, self.R)

    def to_station_record(self):
        return StationRecord(
            stage_name=self.stage_name or "Freestream",
            stage_index=self.stage_index,
            actual_temperature_K=self.T,
            actual_pressure_kPa=self.P / 1000.0,
            actual_velocity_mps=self.V,
            actual_entropy_J_per_kgK=self.s,
            actual_specific_volume_m3_per_kg=self.v,
            ideal_temperature_K=self.T_ideal,
            ideal_pressure_kPa=self.P_ideal / 1000.0,
            ideal_velocity_mps=self.V_ideal,
            ideal_entropy_J_per_kgK=self.s_ideal,
            ideal_specific_volume_m3_per_kg=self.v_ideal,
            cumulative_fuel_air_ratio=self.fuel_air_ratio,
            heat_input_J_per_kg_air=self.Qin,
            compressor_work_J_per_kg_air=self.Wc,
            turbine_work_J_per_kg_air=self.Wt,
            nozzle_choked=self.nozzle_choked,
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
    def station_records(self):
        return [state.to_station_record() for state in self.states]

    def to_dataframe(self):
        frame = pd.DataFrame([record.__dict__ for record in self.station_records])
        frame["fuel_air_ratio"] = frame["cumulative_fuel_air_ratio"]
        return frame


class Stage:
    def __init__(self, name="Stage"):
        self.name = name

    def process(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Subclasses must implement the process method.")
