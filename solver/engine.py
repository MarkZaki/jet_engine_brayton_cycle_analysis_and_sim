from solver.helpers import kelvinToCelsius


class Engine:
    def __init__(self, stages):
        self.stages = stages

    def run(self, initial_state):
        initial_state.update_derived()
        states = [initial_state]

        for index, stage in enumerate(self.stages):
            new_state = stage.process(states[-1])
            new_state.stage_name = stage.name
            new_state.stage_index = index
            new_state.update_derived()
            states.append(new_state)

            print(
                f"{stage.name}: "
                f"actual T={kelvinToCelsius(new_state.T):.2f} degC, "
                f"actual P={new_state.P:.0f} Pa | "
                f"ideal T={kelvinToCelsius(new_state.T_ideal):.2f} degC, "
                f"ideal P={new_state.P_ideal:.0f} Pa"
            )

        return states
