from models.atmosphere import Cp, gamma
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, pressure_from_isentropic_temperature


class Turbine(Stage):
    def __init__(self, eta_t, cp=Cp, eta_mech=0.95, gamma_value=gamma):
        super().__init__("Turbine")
        self.cp = cp
        self.eta_t = eta_t
        self.eta_mech = eta_mech
        self.gamma = gamma_value

    def process(self, state: FlowState) -> FlowState:
        work_required = state.Wc / self.eta_mech
        T4 = state.T - work_required / self.cp
        T4s = state.T - (state.T - T4) / self.eta_t
        P4 = pressure_from_isentropic_temperature(state.T, T4s, state.P, self.gamma)

        work_required_ideal = state.Wc_ideal
        T4_ideal = state.T_ideal - work_required_ideal / self.cp
        P4_ideal = pressure_from_isentropic_temperature(
            state.T_ideal,
            T4_ideal,
            state.P_ideal,
            self.gamma,
        )

        new_state = state.copy()
        new_state.T = T4
        new_state.P = P4
        new_state.s += entropy_change(T4, state.T, P4, state.P, self.cp, state.R)
        new_state.Wt += work_required

        new_state.T_ideal = T4_ideal
        new_state.P_ideal = P4_ideal
        new_state.Wt_ideal += work_required_ideal

        new_state.update_derived()
        return new_state
