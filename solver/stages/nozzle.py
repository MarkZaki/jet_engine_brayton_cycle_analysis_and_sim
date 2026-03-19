import math

from solver.base import Stage

class Nozzle(Stage):
    def __init__(self, cp, Pe=101325, gamma=1.4):
        super().__init__("Nozzle")
        self.cp = cp
        self.Pe = Pe
        self.gamma = gamma

    def process(self, state):
        T4 = state.T
        P4 = state.P
        Pe = self.Pe  # ambient pressure
        # assume expansion to ambient → convert thermal → kinetic
        Te = T4*(Pe/P4)**((self.gamma-1)/self.gamma)  # isentropic expansion to ambient
        Ve = math.sqrt(2 * self.cp * (T4 - Te)) 
        entropy = 0  # for simplicity, assume isentropic expansion in nozzle
        new_state = state.copy()
        new_state.V = Ve
        new_state.s += entropy

        return new_state