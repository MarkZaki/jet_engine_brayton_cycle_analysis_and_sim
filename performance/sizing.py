from __future__ import annotations

import math


def equivalent_diameter(area: float) -> float:
    if area <= 0.0 or not math.isfinite(area):
        return 0.0
    return math.sqrt(4.0 * area / math.pi)


def capture_area(total_air_mass_flow: float, density: float, velocity: float) -> float:
    if total_air_mass_flow <= 0.0 or density <= 0.0 or velocity <= 0.0:
        return 0.0
    return total_air_mass_flow / (density * velocity)
