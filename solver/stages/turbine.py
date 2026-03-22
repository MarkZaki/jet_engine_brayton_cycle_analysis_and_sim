from __future__ import annotations

from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, pressure_from_isentropic_temperature
from solver.maps import mapped_turbine_efficiency


class Turbine(Stage):
    def __init__(
        self,
        eta_t: float,
        eta_mech: float = 0.95,
        exit_velocity: float = 150.0,
        gas=STANDARD_AIR,
        name: str = "Turbine",
        load_keys: tuple[str, ...] = ("compressor",),
        map_enabled: bool = False,
        design_loading: float = 0.22,
        map_sensitivity_loading: float = 0.05,
        map_sensitivity_corrected_flow: float = 0.05,
        min_map_efficiency: float = 0.70,
    ) -> None:
        super().__init__(name)
        self.eta_t = eta_t
        self.eta_mech = eta_mech
        self.exit_velocity = exit_velocity
        self.gas = gas
        self.load_keys = load_keys
        self.map_enabled = map_enabled
        self.design_loading = design_loading
        self.map_sensitivity_loading = map_sensitivity_loading
        self.map_sensitivity_corrected_flow = map_sensitivity_corrected_flow
        self.min_map_efficiency = min_map_efficiency

    def process(self, state: FlowState) -> FlowState:
        tracked_work = sum(state.get_work(key) for key in self.load_keys)
        work_required = (
            tracked_work if tracked_work > 0.0 else state.Wc
        ) / max(self.eta_mech, 1e-9)
        gas_flow_factor = 1.0 + state.fuel_air_ratio
        actual_delta_h = work_required / max(gas_flow_factor, 1e-9)
        loading_parameter = actual_delta_h / max(self.gas.cp_at(state.Tt) * state.Tt, 1e-9)
        eta_actual = mapped_turbine_efficiency(
            base_efficiency=self.eta_t,
            loading_parameter=loading_parameter,
            design_loading=self.design_loading,
            m_dot=state.m_dot_actual,
            Tt_in=state.Tt,
            Pt_in=state.Pt,
            enabled=self.map_enabled,
            sensitivity_loading=self.map_sensitivity_loading,
            sensitivity_flow=self.map_sensitivity_corrected_flow,
            min_efficiency=self.min_map_efficiency,
        )

        Tt4 = self.gas.temperature_from_enthalpy_change(state.Tt, -actual_delta_h)
        Tt4s = self.gas.temperature_from_enthalpy_change(state.Tt, -(actual_delta_h / max(eta_actual, 1e-9)))
        Pt4 = pressure_from_isentropic_temperature(state.Tt, Tt4s, state.Pt, self.gas)

        tracked_work_ideal = sum(state.get_work(key, ideal=True) for key in self.load_keys)
        work_required_ideal = tracked_work_ideal if tracked_work_ideal > 0.0 else state.Wc_ideal
        gas_flow_factor_ideal = 1.0 + state.fuel_air_ratio_ideal
        ideal_delta_h_branch = work_required_ideal / max(gas_flow_factor_ideal, 1e-9)
        Tt4_ideal = self.gas.temperature_from_enthalpy_change(state.Tt_ideal, -ideal_delta_h_branch)
        Pt4_ideal = pressure_from_isentropic_temperature(state.Tt_ideal, Tt4_ideal, state.Pt_ideal, self.gas)

        new_state = state.copy()
        new_state.set_actual_total(Tt4, Pt4, self.exit_velocity)
        new_state.s += entropy_change(Tt4, state.Tt, Pt4, state.Pt, self.gas)
        new_state.Wt += work_required

        new_state.set_ideal_total(Tt4_ideal, Pt4_ideal, self.exit_velocity)
        new_state.Wt_ideal += work_required_ideal
        if eta_actual < self.eta_t - 0.02:
            new_state.add_warning(f"{self.name} off-design map reduced efficiency to {eta_actual:.3f}.")

        new_state.update_derived()
        return new_state
