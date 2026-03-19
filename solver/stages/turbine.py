from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, pressure_from_isentropic_temperature


class Turbine(Stage):
    def __init__(self, eta_t, eta_mech=0.95, exit_velocity=150.0, gas=STANDARD_AIR):
        super().__init__("Turbine")
        self.eta_t = eta_t
        self.eta_mech = eta_mech
        self.exit_velocity = exit_velocity
        self.gas = gas

    def process(self, state: FlowState) -> FlowState:
        work_required = state.Wc / self.eta_mech
        gas_flow_factor = 1.0 + state.fuel_air_ratio
        Tt4 = state.Tt - work_required / (gas_flow_factor * self.gas.cp)
        Tt4s = state.Tt - (state.Tt - Tt4) / self.eta_t
        Pt4 = pressure_from_isentropic_temperature(state.Tt, Tt4s, state.Pt, self.gas.gamma)

        work_required_ideal = state.Wc_ideal
        gas_flow_factor_ideal = 1.0 + state.fuel_air_ratio_ideal
        Tt4_ideal = state.Tt_ideal - work_required_ideal / (gas_flow_factor_ideal * self.gas.cp)
        Pt4_ideal = pressure_from_isentropic_temperature(
            state.Tt_ideal,
            Tt4_ideal,
            state.Pt_ideal,
            self.gas.gamma,
        )

        new_state = state.copy()
        new_state.set_actual_total(Tt4, Pt4, self.exit_velocity)
        new_state.s += entropy_change(Tt4, state.Tt, Pt4, state.Pt, self.gas.cp, state.R)
        new_state.Wt += work_required

        new_state.set_ideal_total(Tt4_ideal, Pt4_ideal, self.exit_velocity)
        new_state.Wt_ideal += work_required_ideal

        new_state.update_derived()
        return new_state
