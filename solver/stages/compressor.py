from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, isentropic_temperature


class Compressor(Stage):
    def __init__(self, pressure_ratio, eta_c, gas=STANDARD_AIR):
        super().__init__("Compressor")
        self.rp = pressure_ratio
        self.eta_c = eta_c
        self.gas = gas

    def process(self, state: FlowState) -> FlowState:
        P2 = state.P * self.rp
        T2s = isentropic_temperature(state.T, P2, state.P, self.gas.gamma)
        T2 = state.T + (T2s - state.T) / self.eta_c

        P2_ideal = state.P_ideal * self.rp
        T2_ideal = isentropic_temperature(state.T_ideal, P2_ideal, state.P_ideal, self.gas.gamma)

        new_state = state.copy()
        new_state.T = T2
        new_state.P = P2
        new_state.s += entropy_change(T2, state.T, P2, state.P, self.gas.cp, state.R)
        new_state.Wc += self.gas.cp * (T2 - state.T)

        new_state.T_ideal = T2_ideal
        new_state.P_ideal = P2_ideal
        new_state.Wc_ideal += self.gas.cp * (T2_ideal - state.T_ideal)

        new_state.update_derived()
        return new_state
