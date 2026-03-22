from __future__ import annotations

from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, isentropic_temperature
from solver.maps import mapped_compressor_efficiency


class Compressor(Stage):
    def __init__(
        self,
        pressure_ratio: float,
        eta_c: float,
        exit_velocity: float = 120.0,
        gas=STANDARD_AIR,
        name: str = "Compressor",
        work_key: str = "compressor",
        map_enabled: bool = False,
        design_pressure_ratio: float | None = None,
        design_corrected_flow: float | None = None,
        map_stream: str = "core",
        map_sensitivity_pressure_ratio: float = 0.06,
        map_sensitivity_corrected_flow: float = 0.05,
        min_map_efficiency: float = 0.70,
    ) -> None:
        super().__init__(name)
        self.rp = pressure_ratio
        self.eta_c = eta_c
        self.exit_velocity = exit_velocity
        self.gas = gas
        self.work_key = work_key
        self.map_enabled = map_enabled
        self.design_pressure_ratio = design_pressure_ratio if design_pressure_ratio is not None else pressure_ratio
        self.design_corrected_flow = design_corrected_flow
        self.map_stream = map_stream
        self.map_sensitivity_pressure_ratio = map_sensitivity_pressure_ratio
        self.map_sensitivity_corrected_flow = map_sensitivity_corrected_flow
        self.min_map_efficiency = min_map_efficiency

    def process(self, state: FlowState) -> FlowState:
        map_mass_flow = state.total_air_mass_flow if self.map_stream == "total" else state.m_dot
        eta_actual = mapped_compressor_efficiency(
            base_efficiency=self.eta_c,
            pressure_ratio=self.rp,
            design_pressure_ratio=self.design_pressure_ratio,
            m_dot=map_mass_flow,
            Tt_in=state.Tt,
            Pt_in=state.Pt,
            design_corrected_flow=self.design_corrected_flow,
            enabled=self.map_enabled,
            sensitivity_pressure_ratio=self.map_sensitivity_pressure_ratio,
            sensitivity_flow=self.map_sensitivity_corrected_flow,
            min_efficiency=self.min_map_efficiency,
        )
        Pt2 = state.Pt * self.rp
        Tt2s = isentropic_temperature(state.Tt, Pt2, state.Pt, self.gas)
        ideal_delta_h = self.gas.delta_h(Tt2s, state.Tt)
        Tt2 = self.gas.temperature_from_enthalpy_change(state.Tt, ideal_delta_h / max(eta_actual, 1e-9))

        Pt2_ideal = state.Pt_ideal * self.rp
        Tt2_ideal = isentropic_temperature(state.Tt_ideal, Pt2_ideal, state.Pt_ideal, self.gas)

        new_state = state.copy()
        new_state.set_actual_total(Tt2, Pt2, self.exit_velocity)
        new_state.s += entropy_change(Tt2, state.Tt, Pt2, state.Pt, self.gas)
        actual_work = self.gas.delta_h(Tt2, state.Tt)
        new_state.Wc += actual_work
        new_state.add_work(self.work_key, actual_work)

        new_state.set_ideal_total(Tt2_ideal, Pt2_ideal, self.exit_velocity)
        ideal_work = self.gas.delta_h(Tt2_ideal, state.Tt_ideal)
        new_state.Wc_ideal += ideal_work
        new_state.add_work(self.work_key, ideal_work, ideal=True)
        if eta_actual < self.eta_c - 0.02:
            new_state.add_warning(f"{self.name} off-design map reduced efficiency to {eta_actual:.3f}.")

        new_state.update_derived()
        return new_state
