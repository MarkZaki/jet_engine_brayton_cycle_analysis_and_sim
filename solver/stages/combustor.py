from models.atmosphere import Cp
from solver.base import FlowState, Stage
from solver.cycle import entropy_change


class Combustor(Stage):
    def __init__(self, T3, pressure_loss=0.05, cp=Cp):
        super().__init__("Combustor")
        self.T3 = T3
        self.pressure_loss = pressure_loss
        self.cp = cp

    def process(self, state: FlowState) -> FlowState:
        P3 = state.P * (1.0 - self.pressure_loss)
        P3_ideal = state.P_ideal

        new_state = state.copy()
        new_state.T = self.T3
        new_state.P = P3
        new_state.s += entropy_change(self.T3, state.T, P3, state.P, self.cp, state.R)
        new_state.Qin += self.cp * (self.T3 - state.T)

        new_state.T_ideal = self.T3
        new_state.P_ideal = P3_ideal
        new_state.s_ideal += entropy_change(
            self.T3,
            state.T_ideal,
            P3_ideal,
            state.P_ideal,
            self.cp,
            state.R,
        )
        new_state.Qin_ideal += self.cp * (self.T3 - state.T_ideal)

        new_state.update_derived()
        return new_state
