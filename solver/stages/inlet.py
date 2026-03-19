from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import (
    entropy_change,
)


class Inlet(Stage):
    def __init__(
        self,
        pressure_recovery=0.98,
        exit_velocity=85.0,
        gas=STANDARD_AIR,
    ):
        super().__init__("Inlet")
        self.pressure_recovery = pressure_recovery
        self.exit_velocity = exit_velocity
        self.gas = gas

    def process(self, state: FlowState) -> FlowState:
        Tt2 = state.Tt
        Pt2 = self.pressure_recovery * state.Pt
        Tt2_ideal = state.Tt_ideal
        Pt2_ideal = state.Pt_ideal

        new_state = state.copy()
        new_state.set_actual_total(Tt2, Pt2, self.exit_velocity)
        new_state.s += entropy_change(Tt2, state.Tt, Pt2, state.Pt, self.gas.cp, state.R)

        new_state.set_ideal_total(Tt2_ideal, Pt2_ideal, self.exit_velocity)
        new_state.s_ideal = state.s_ideal

        new_state.update_derived()
        return new_state
