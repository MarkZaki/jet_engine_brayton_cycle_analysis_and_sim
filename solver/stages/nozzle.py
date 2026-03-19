import math

from models.atmosphere import gamma
from solver.base import FlowState, Stage
from solver.cycle import isentropic_temperature


class Nozzle(Stage):
    def __init__(self, cp, Pe=101325.0, gamma=gamma):
        super().__init__("Nozzle")
        self.cp = cp
        self.Pe = Pe
        self.gamma = gamma

    def _expand(self, temperature, pressure):
        if pressure <= self.Pe:
            return temperature, pressure, 0.0

        Te = isentropic_temperature(temperature, self.Pe, pressure, self.gamma)
        Ve = math.sqrt(max(0.0, 2.0 * self.cp * (temperature - Te)))
        return Te, self.Pe, Ve

    def process(self, state: FlowState) -> FlowState:
        T_exit, P_exit, V_exit = self._expand(state.T, state.P)
        T_exit_ideal, P_exit_ideal, V_exit_ideal = self._expand(state.T_ideal, state.P_ideal)

        new_state = state.copy()
        new_state.T = T_exit
        new_state.P = P_exit
        new_state.V = V_exit

        new_state.T_ideal = T_exit_ideal
        new_state.P_ideal = P_exit_ideal
        new_state.V_ideal = V_exit_ideal

        new_state.update_derived()
        return new_state
