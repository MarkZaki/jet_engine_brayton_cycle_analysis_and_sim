"""Combustor stage placeholder."""
from models.atmosphere import Cp
from solver.base import Stage


class Combustor(Stage):
    def __init__(self, T3, pressure_loss=0.05, cp=Cp):
        super().__init__("Combustor")
        self.T3 = T3
        self.pressure_loss = pressure_loss
        self.cp = cp

    def process(self, state):
      new_state = state.copy()
      entropy = self.cp * (self.T3 - state.T) - self.cp * state.T * self.pressure_loss
      new_state.s += entropy
      T2 = state.T
      new_state.T = self.T3
      new_state.P = state.P * (1 - self.pressure_loss)

      Qin = self.cp * (self.T3 - T2)
      new_state.Qin += Qin

      return new_state