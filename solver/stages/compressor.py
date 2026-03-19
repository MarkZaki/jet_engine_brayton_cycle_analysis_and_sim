"""Compressor stage placeholder."""
import math

from models.atmosphere import Cp, gamma
from solver.base import Stage, FlowState

class Compressor(Stage):
    def __init__(self, pressure_ratio, eta_c, gamma=gamma, cp=Cp):
        super().__init__("Compressor")
        self.rp = pressure_ratio
        self.eta_c = eta_c
        self.gamma = gamma
        self.cp = cp

    def process(self, state: FlowState) -> FlowState:
        T1, P1 = state.T, state.P

        P2 = P1 * self.rp

        # isentropic temperature
        T2s = T1 * (self.rp)**((self.gamma - 1)/self.gamma)

        # real temperature
        T2 = T1 + (T2s - T1) / self.eta_c

        entropy = self.cp * math.log(T2 - T1, math.e) - self.cp * T1 * math.log(P2/P1, math.e)

        new_state = state.copy()
        new_state.T = T2
        new_state.P = P2
        new_state.s += entropy
        Wc = self.cp * (T2 - T1)
        new_state.Wc += Wc

        return new_state