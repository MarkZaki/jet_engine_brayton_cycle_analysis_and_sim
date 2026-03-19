from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, isentropic_temperature


class Compressor(Stage):
    def __init__(self, pressure_ratio, eta_c, exit_velocity=120.0, gas=STANDARD_AIR):
        super().__init__("Compressor")
        self.rp = pressure_ratio
        self.eta_c = eta_c
        self.exit_velocity = exit_velocity
        self.gas = gas

    def process(self, state: FlowState) -> FlowState:
        Pt2 = state.Pt * self.rp
        Tt2s = isentropic_temperature(state.Tt, Pt2, state.Pt, self.gas.gamma)
        Tt2 = state.Tt + (Tt2s - state.Tt) / self.eta_c

        Pt2_ideal = state.Pt_ideal * self.rp
        Tt2_ideal = isentropic_temperature(state.Tt_ideal, Pt2_ideal, state.Pt_ideal, self.gas.gamma)

        new_state = state.copy()
        new_state.set_actual_total(Tt2, Pt2, self.exit_velocity)
        new_state.s += entropy_change(Tt2, state.Tt, Pt2, state.Pt, self.gas.cp, state.R)
        new_state.Wc += self.gas.cp * (Tt2 - state.Tt)

        new_state.set_ideal_total(Tt2_ideal, Pt2_ideal, self.exit_velocity)
        new_state.Wc_ideal += self.gas.cp * (Tt2_ideal - state.Tt_ideal)

        new_state.update_derived()
        return new_state
