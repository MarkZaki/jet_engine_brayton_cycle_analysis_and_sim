from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, pressure_from_isentropic_temperature


class Turbine(Stage):
    def __init__(self, eta_t, eta_mech=0.95, gas=STANDARD_AIR):
        super().__init__("Turbine")
        self.eta_t = eta_t
        self.eta_mech = eta_mech
        self.gas = gas

    def process(self, state: FlowState) -> FlowState:
        work_required = state.Wc / self.eta_mech
        gas_flow_factor = 1.0 + state.fuel_air_ratio
        T4 = state.T - work_required / (gas_flow_factor * self.gas.cp)
        T4s = state.T - (state.T - T4) / self.eta_t
        P4 = pressure_from_isentropic_temperature(state.T, T4s, state.P, self.gas.gamma)

        work_required_ideal = state.Wc_ideal
        gas_flow_factor_ideal = 1.0 + state.fuel_air_ratio_ideal
        T4_ideal = state.T_ideal - work_required_ideal / (gas_flow_factor_ideal * self.gas.cp)
        P4_ideal = pressure_from_isentropic_temperature(
            state.T_ideal,
            T4_ideal,
            state.P_ideal,
            self.gas.gamma,
        )

        new_state = state.copy()
        new_state.T = T4
        new_state.P = P4
        new_state.s += entropy_change(T4, state.T, P4, state.P, self.gas.cp, state.R)
        new_state.Wt += work_required

        new_state.T_ideal = T4_ideal
        new_state.P_ideal = P4_ideal
        new_state.Wt_ideal += work_required_ideal

        new_state.update_derived()
        return new_state
