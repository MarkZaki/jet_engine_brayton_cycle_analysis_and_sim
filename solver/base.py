from models.atmosphere import Cp, R, gamma
from solver.cycle import specific_volume


class FlowState:
    def __init__(
        self,
        T,
        P,
        V=0.0,
        m_dot=1.0,
        Wc=0.0,
        Wt=0.0,
        Qin=0.0,
        cp=Cp,
        gamma_value=gamma,
        gas_constant=R,
    ):
        self.T = T
        self.P = P
        self.V = V
        self.m_dot = m_dot
        self.cp = cp
        self.gamma = gamma_value
        self.R = gas_constant

        self.s = 0.0
        self.v = 0.0
        self.Wc = Wc
        self.Wt = Wt
        self.Qin = Qin

        self.T_ideal = T
        self.P_ideal = P
        self.V_ideal = V
        self.s_ideal = 0.0
        self.v_ideal = 0.0
        self.Wc_ideal = Wc
        self.Wt_ideal = Wt
        self.Qin_ideal = Qin

        self.stage_name = ""
        self.stage_index = -1

        self.update_derived()

    def copy(self):
        new = FlowState(
            self.T,
            self.P,
            self.V,
            self.m_dot,
            self.Wc,
            self.Wt,
            self.Qin,
            self.cp,
            self.gamma,
            self.R,
        )
        new.s = self.s
        new.v = self.v
        new.T_ideal = self.T_ideal
        new.P_ideal = self.P_ideal
        new.V_ideal = self.V_ideal
        new.s_ideal = self.s_ideal
        new.v_ideal = self.v_ideal
        new.Wc_ideal = self.Wc_ideal
        new.Wt_ideal = self.Wt_ideal
        new.Qin_ideal = self.Qin_ideal
        new.stage_name = self.stage_name
        new.stage_index = self.stage_index
        return new

    def update_derived(self):
        self.v = specific_volume(self.T, self.P, self.R)
        self.v_ideal = specific_volume(self.T_ideal, self.P_ideal, self.R)


class Stage:
    def __init__(self, name="Stage"):
        self.name = name

    def process(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Subclasses must implement the process method.")
