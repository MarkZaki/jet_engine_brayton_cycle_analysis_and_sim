class FlowState:
    def __init__(self, T, P, V=0, m_dot=1.0, Wc=0.0, Wt=0.0, Qin=0.0):
        self.T = T
        self.P = P
        self.V = V
        self.m_dot = m_dot
        self.s = 0  # entropy
        self.Wc = Wc
        self.Wt = Wt
        self.Qin = Qin
        self.stage_name = ""
        self.stage_index = -1
        self.Vel_in = 0  # Added to track inlet velocity
        self.Vel_out = 0  # Added to track outlet velocity

    def copy(self):
        new = FlowState(self.T, self.P, self.V, self.m_dot, self.Wc, self.Wt, self.Qin)
        new.stage_name = self.stage_name
        new.stage_index = self.stage_index
        new.Vel_in = self.Vel_in
        new.Vel_out = self.Vel_out
        new.s = self.s
        return new

class Stage:
    def __init__(self, name="Stage"):
        self.name = name

    def process(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Subclasses must implement the process method.")