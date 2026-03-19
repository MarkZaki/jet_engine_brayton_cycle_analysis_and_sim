"""Turbine stage placeholder."""
import math

from models.atmosphere import Cp
from solver.base import Stage


class Turbine(Stage):
    def __init__(self, eta_t, cp=Cp, eta_mech=0.95):
        super().__init__("Turbine")
        self.cp = cp
        self.eta_t = eta_t
        self.eta_mech = eta_mech
        self.Wc = 0  # will be set by compressor

    def process(self, state):
      T3 = state.T

      # turbine provides compressor work
      Wt = state.Wc / self.eta_mech  # what compressor needed

      T4 = T3 - Wt / self.cp

      entropy = 0 # for simplicity, assume isentropic expansion in turbine

      new_state = state.copy()
      new_state.T = T4
      new_state.P = state.P * 0.9
      new_state.s += entropy

      new_state.Wt += Wt

      return new_state