import numpy as np

from visualization.diagrams import PV_diagram, TP_diagram, TS_diagram, performance_diagram


def _annotate_points(ax, stations, x_key, y_key):
    for station in stations:
        ax.annotate(
            station["label"],
            (station[x_key], station[y_key]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )


def plot_PV(states):
    import matplotlib.pyplot as plt

    data = PV_diagram(states)
    actual_v, actual_p, _, _ = zip(*data["actual"]["curve"])
    ideal_v, ideal_p, _, _ = zip(*data["ideal"]["curve"])

    fig, ax = plt.subplots()
    ax.plot(ideal_v, ideal_p, linestyle="--", linewidth=2, label="Theoretical")
    ax.plot(actual_v, actual_p, linewidth=2, label="Actual")
    _annotate_points(ax, data["actual"]["stations"], "v", "P")
    ax.set_title("P-v Diagram")
    ax.set_xlabel("Specific Volume (m^3/kg)")
    ax.set_ylabel("Pressure (Pa)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_TS(states):
    import matplotlib.pyplot as plt

    data = TS_diagram(states)
    _, _, actual_s, actual_t = zip(*data["actual"]["curve"])
    _, _, ideal_s, ideal_t = zip(*data["ideal"]["curve"])

    fig, ax = plt.subplots()
    ax.plot(ideal_s, ideal_t, linestyle="--", linewidth=2, label="Theoretical")
    ax.plot(actual_s, actual_t, linewidth=2, label="Actual")
    _annotate_points(ax, data["actual"]["stations"], "s", "T")
    ax.set_title("T-s Diagram")
    ax.set_xlabel("Entropy (J/kg-K)")
    ax.set_ylabel("Temperature (K)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_TP(states):
    import matplotlib.pyplot as plt

    data = TP_diagram(states)
    _, actual_p, _, actual_t = zip(*data["actual"]["curve"])
    _, ideal_p, _, ideal_t = zip(*data["ideal"]["curve"])

    fig, ax = plt.subplots()
    ax.plot(ideal_p, ideal_t, linestyle="--", linewidth=2, label="Theoretical")
    ax.plot(actual_p, actual_t, linewidth=2, label="Actual")
    _annotate_points(ax, data["actual"]["stations"], "P", "T")
    ax.set_title("T-P Diagram")
    ax.set_xlabel("Pressure (Pa)")
    ax.set_ylabel("Temperature (K)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_performance(states):
    import matplotlib.pyplot as plt

    data = performance_diagram(states)
    x = np.arange(len(data["stage_names"]))
    width = 0.35

    fig, ax = plt.subplots()
    ax.bar(x - width / 2, data["ideal_net"], width, label="Theoretical net work")
    ax.bar(x + width / 2, data["actual_net"], width, label="Actual net work")
    ax.set_title("Net Specific Work by Stage")
    ax.set_xlabel("Stage")
    ax.set_ylabel("Specific Work (J/kg)")
    ax.set_xticks(x)
    ax.set_xticklabels(data["stage_names"], rotation=20)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()
