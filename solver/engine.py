"""Engine orchestration placeholder."""
from solver.helpers import kelvinToCelsius


class Engine:
    def __init__(self, stages):
        self.stages = stages

    def run(self, initial_state):
      states = [initial_state]

      for i, stage in enumerate(self.stages):
          new_state = stage.process(states[-1])
          new_state.stage_name = stage.name
          new_state.stage_index = i
          states.append(new_state)
          print(stage.name,":", "Temperature:", kelvinToCelsius(new_state.T), "°C", "Pressure:", new_state.P, "Pa",stage.name,":", "Compressor Work:", new_state.Wc, "J", "Turbine Work:", new_state.Wt, "J", "Heat Added:", new_state.Qin, "J", "Entropy:", new_state.s, "J/K")
          print("-" * 50)

      return states