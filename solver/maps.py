from __future__ import annotations

from solver.cycle import corrected_mass_flow


def mapped_compressor_efficiency(
    base_efficiency: float,
    pressure_ratio: float,
    design_pressure_ratio: float,
    m_dot: float,
    Tt_in: float,
    Pt_in: float,
    design_corrected_flow: float | None,
    enabled: bool,
    sensitivity_pressure_ratio: float,
    sensitivity_flow: float,
    min_efficiency: float,
) -> float:
    if not enabled:
        return base_efficiency

    actual_corrected_flow = corrected_mass_flow(m_dot, Tt_in, Pt_in)
    reference_corrected_flow = design_corrected_flow if design_corrected_flow is not None else actual_corrected_flow
    pr_term = (pressure_ratio / max(design_pressure_ratio, 1e-9)) - 1.0
    flow_term = (actual_corrected_flow / max(reference_corrected_flow, 1e-9)) - 1.0
    scale = 1.0 - sensitivity_pressure_ratio * pr_term**2 - sensitivity_flow * flow_term**2
    return max(min_efficiency, min(base_efficiency, base_efficiency * scale))


def mapped_turbine_efficiency(
    base_efficiency: float,
    loading_parameter: float,
    design_loading: float,
    m_dot: float,
    Tt_in: float,
    Pt_in: float,
    enabled: bool,
    sensitivity_loading: float,
    sensitivity_flow: float,
    min_efficiency: float,
) -> float:
    if not enabled:
        return base_efficiency

    actual_corrected_flow = corrected_mass_flow(m_dot, Tt_in, Pt_in)
    reference_corrected_flow = corrected_mass_flow(m_dot, max(Tt_in, 1.0), max(Pt_in, 1.0))
    loading_term = (loading_parameter / max(design_loading, 1e-9)) - 1.0
    flow_term = (actual_corrected_flow / max(reference_corrected_flow, 1e-9)) - 1.0
    scale = 1.0 - sensitivity_loading * loading_term**2 - sensitivity_flow * flow_term**2
    return max(min_efficiency, min(base_efficiency, base_efficiency * scale))
