from visualization.diagrams import PV_diagram,TP_diagram,TS_diagram,performance_diagram


def plot_PV(states):
    """Plot a P-V diagram."""
    import matplotlib.pyplot as plt

    data = PV_diagram(states)
    V, P = zip(*data)

    plt.figure()
    plt.plot(V, P, marker='o')
    plt.title('P-V Diagram')
    plt.xlabel('Volume (m^3)')
    plt.ylabel('Pressure (Pa)')
    plt.grid()
    plt.show()

def plot_TS(states):
    """Plot a T-S diagram."""
    import matplotlib.pyplot as plt

    data = TS_diagram(states)
    s, T = zip(*data)

    plt.figure()
    plt.plot(s, T, marker='o')
    plt.title('T-S Diagram')
    plt.xlabel('Entropy (J/K)')
    plt.ylabel('Temperature (K)')
    plt.grid()
    plt.show()

def plot_TP(states):
    """Plot a T-P diagram."""
    import matplotlib.pyplot as plt

    data = TP_diagram(states)
    P, T = zip(*data)

    plt.figure()
    plt.plot(P, T, marker='o')
    plt.title('T-P Diagram')
    plt.xlabel('Pressure (Pa)')
    plt.ylabel('Temperature (K)')
    plt.grid()
    plt.show()

def plot_performance(states):
    """Plot performance metrics."""
    import matplotlib.pyplot as plt

    data = performance_diagram(states)
    stage_names, Wc, Wt = zip(*data)

    plt.figure()
    plt.bar(stage_names, Wc, label='Compressor Work (Wc)', alpha=0.7)
    plt.bar(stage_names, Wt, label='Turbine Work (Wt)', alpha=0.7)
    plt.title('Performance Metrics')
    plt.xlabel('Stage')
    plt.ylabel('Work (J)')
    plt.legend()
    plt.grid()
    plt.show()