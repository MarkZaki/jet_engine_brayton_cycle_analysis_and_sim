"""Inlet stage placeholder."""
from solver.base import Stage, FlowState
class Inlet(Stage):
    def __init__(self, pressure_recovery=0.98):
        super().__init__("Inlet")
        self.pressure_recovery = pressure_recovery

    def process(self, state: FlowState) -> FlowState:
        new_state = state.copy()
        new_state.P = state.P * self.pressure_recovery
        return new_state