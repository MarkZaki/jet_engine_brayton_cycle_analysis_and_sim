classdef EngineSim
    properties (Constant, Access = private)
        MIN_POSITIVE = 1.0e-9;
    end

    methods (Static)
        function [result, summary] = main(config)
            if nargin < 1
                config = [];
            end

            result = EngineSim.run_engine_case(config);
            summary = EngineSim.summarize_result(result, result.config.flight_speed);

            fprintf('---- BRAYTON CYCLE RESULTS ----\n');
            fprintf('Thrust: %.2f N\n', summary.thrust_N);
            fprintf('Specific thrust: %.2f N/(kg/s)\n', summary.specific_thrust_N_per_kg_s);
            fprintf('Fuel-air ratio: %.5f\n', summary.fuel_air_ratio);
            fprintf('Fuel flow: %.4f kg/s\n', summary.fuel_flow_kg_s);
            fprintf('Specific impulse: %.2f s\n', summary.specific_impulse_s);
            fprintf('Thermal efficiency: %.4f\n', summary.thermal_efficiency);
            fprintf('Propulsive efficiency: %.4f\n', summary.propulsive_efficiency);
            fprintf('Overall efficiency: %.4f\n', summary.overall_efficiency);
            fprintf('Back work ratio: %.4f\n', summary.bwr);
            fprintf('Nozzle choked: %d\n', summary.nozzle_choked);
            fprintf('Exit Mach: %.3f\n', summary.exit_mach);
            for idx = 1:numel(summary.warnings)
                fprintf('Warning: %s\n', summary.warnings{idx});
            end

            figures = {
                EngineSim.plot_PV(result, true)
                EngineSim.plot_TS(result, true)
                EngineSim.plot_TP(result, true)
                EngineSim.plot_performance(result, true)
                EngineSim.plot_engine_flow(result, false, true)
                EngineSim.plot_engine_flow(result, true, true)
            };
            figure_names = {
                'PV'
                'TS'
                'TP'
                'performance'
                'engine_flow_actual'
                'engine_flow_ideal'
            };

            if result.config.export_png
                output_dir = EngineSim.export_main_outputs(result, summary, figures, figure_names);
                fprintf('Saved MATLAB outputs: %s\n', output_dir);
            end
        end

        function config = get_default_engine_config()
            config = struct( ...
                'altitude_m', 0.0, ...
                'ambient_temperature', [], ...
                'ambient_pressure', [], ...
                'flight_input_mode', 'speed', ...
                'flight_speed', 180.0, ...
                'flight_mach_number', 0.0, ...
                'mass_flow_rate', 12.0, ...
                'pressure_recovery', 0.98, ...
                'diffuser_exit_velocity', 60.0, ...
                'compressor_pressure_ratio', 8.0, ...
                'compressor_efficiency', 0.85, ...
                'compressor_exit_velocity', 70.0, ...
                'turbine_inlet_temperature', 1400.0, ...
                'combustor_pressure_loss', 0.05, ...
                'combustor_efficiency', 0.98, ...
                'combustor_exit_velocity', 45.0, ...
                'turbine_efficiency', 0.90, ...
                'mechanical_efficiency', 0.97, ...
                'turbine_exit_velocity', 85.0, ...
                'nozzle_efficiency', 0.96, ...
                'gas_name', 'Air', ...
                'gas_cp', 1004.5, ...
                'gas_gamma', 1.4, ...
                'gas_R', [], ...
                'fuel_lower_heating_value', 43.0e6, ...
                'export_png', false, ...
                'verbose', true ...
            );
        end

        function config = prepare_config(config)
            defaults = EngineSim.get_default_engine_config();
            if nargin < 1 || isempty(config)
                config = defaults;
            else
                config = EngineSim.merge_config(defaults, config);
            end

            atmosphere = EngineSim.isa_atmosphere(config.altitude_m);
            if isempty(config.ambient_temperature)
                config.ambient_temperature = atmosphere.temperature;
            end
            if isempty(config.ambient_pressure)
                config.ambient_pressure = atmosphere.pressure;
            end

            if strcmpi(config.flight_input_mode, 'mach')
                gas = EngineSim.build_gas_from_config(config);
                config.flight_speed = config.flight_mach_number * ...
                    EngineSim.speed_of_sound(config.ambient_temperature, gas);
            end

            EngineSim.validate_config(config);
        end

        function result = run_engine_case(config)
            if nargin < 1
                config = [];
            end

            runtime_config = EngineSim.prepare_config(config);
            gas = EngineSim.build_gas_from_config(runtime_config);
            cp = gas.cp;
            states = EngineSim.build_initial_state(runtime_config, gas);

            station0 = states(1);
            Tt0 = station0.Tt;
            Pt0 = station0.Pt;

            [states, inlet_state] = EngineSim.append_total_state( ...
                states, ...
                'Inlet', ...
                Tt0, ...
                Pt0 * runtime_config.pressure_recovery, ...
                runtime_config.diffuser_exit_velocity, ...
                Tt0, ...
                Pt0, ...
                runtime_config.diffuser_exit_velocity ...
            );

            Tt2s = inlet_state.Tt * runtime_config.compressor_pressure_ratio ^ ...
                ((gas.gamma - 1.0) / gas.gamma);
            Tt2 = inlet_state.Tt + (Tt2s - inlet_state.Tt) / runtime_config.compressor_efficiency;
            [states, compressor_state] = EngineSim.append_total_state( ...
                states, ...
                'Compressor', ...
                Tt2, ...
                inlet_state.Pt * runtime_config.compressor_pressure_ratio, ...
                runtime_config.compressor_exit_velocity, ...
                Tt2s, ...
                inlet_state.Pt_ideal * runtime_config.compressor_pressure_ratio, ...
                runtime_config.compressor_exit_velocity ...
            );
            compressor_state.Wc = inlet_state.Wc + cp * (compressor_state.Tt - inlet_state.Tt);
            compressor_state.Wc_ideal = ...
                inlet_state.Wc_ideal + cp * (compressor_state.Tt_ideal - inlet_state.Tt_ideal);
            compressor_state = EngineSim.update_state_derived(compressor_state);
            states(end) = compressor_state;

            combustor_total_pressure = compressor_state.Pt * (1.0 - runtime_config.combustor_pressure_loss);
            [states, combustor_state] = EngineSim.append_total_state( ...
                states, ...
                'Combustor', ...
                runtime_config.turbine_inlet_temperature, ...
                combustor_total_pressure, ...
                runtime_config.combustor_exit_velocity, ...
                runtime_config.turbine_inlet_temperature, ...
                compressor_state.Pt_ideal, ...
                runtime_config.combustor_exit_velocity ...
            );
            combustor_state.Wc = compressor_state.Wc;
            combustor_state.Wc_ideal = compressor_state.Wc_ideal;
            combustor_state.Qin = compressor_state.Qin + cp * (combustor_state.Tt - compressor_state.Tt);
            combustor_state.Qin_ideal = ...
                compressor_state.Qin_ideal + cp * (combustor_state.Tt_ideal - compressor_state.Tt_ideal);
            combustor_state.fuel_air_ratio = combustor_state.Qin / ...
                (runtime_config.combustor_efficiency * runtime_config.fuel_lower_heating_value);
            combustor_state.fuel_air_ratio_ideal = ...
                combustor_state.Qin_ideal / runtime_config.fuel_lower_heating_value;
            combustor_state = EngineSim.update_state_derived(combustor_state);
            states(end) = combustor_state;

            required_turbine_work = (compressor_state.Wc - inlet_state.Wc) / runtime_config.mechanical_efficiency;
            required_turbine_work_ideal = compressor_state.Wc_ideal - inlet_state.Wc_ideal;
            delta_t_turbine = required_turbine_work / ...
                max(cp * (1.0 + combustor_state.fuel_air_ratio), EngineSim.MIN_POSITIVE);
            delta_t_turbine_ideal = required_turbine_work_ideal / ...
                max(cp * (1.0 + combustor_state.fuel_air_ratio_ideal), EngineSim.MIN_POSITIVE);
            Tt4 = combustor_state.Tt - delta_t_turbine;
            Tt4_ideal = combustor_state.Tt_ideal - delta_t_turbine_ideal;
            Tt4s = combustor_state.Tt - (combustor_state.Tt - Tt4) / runtime_config.turbine_efficiency;
            Pt4 = combustor_state.Pt * ...
                (Tt4s / max(combustor_state.Tt, EngineSim.MIN_POSITIVE)) ^ (gas.gamma / (gas.gamma - 1.0));
            Pt4_ideal = combustor_state.Pt_ideal * ...
                (Tt4_ideal / max(combustor_state.Tt_ideal, EngineSim.MIN_POSITIVE)) ^ ...
                (gas.gamma / (gas.gamma - 1.0));

            [states, turbine_state] = EngineSim.append_total_state( ...
                states, ...
                'Turbine', ...
                Tt4, ...
                Pt4, ...
                runtime_config.turbine_exit_velocity, ...
                Tt4_ideal, ...
                Pt4_ideal, ...
                runtime_config.turbine_exit_velocity ...
            );
            turbine_state.Wc = combustor_state.Wc;
            turbine_state.Wc_ideal = combustor_state.Wc_ideal;
            turbine_state.Qin = combustor_state.Qin;
            turbine_state.Qin_ideal = combustor_state.Qin_ideal;
            turbine_state.fuel_air_ratio = combustor_state.fuel_air_ratio;
            turbine_state.fuel_air_ratio_ideal = combustor_state.fuel_air_ratio_ideal;
            turbine_state.Wt = combustor_state.Wt + required_turbine_work;
            turbine_state.Wt_ideal = combustor_state.Wt_ideal + required_turbine_work_ideal;
            turbine_state = EngineSim.update_state_derived(turbine_state);
            states(end) = turbine_state;

            actual_nozzle = EngineSim.nozzle_exit_state( ...
                turbine_state.Tt, ...
                turbine_state.Pt, ...
                runtime_config.ambient_pressure, ...
                gas, ...
                runtime_config.nozzle_efficiency, ...
                turbine_state.m_dot_actual ...
            );
            ideal_nozzle = EngineSim.nozzle_exit_state( ...
                turbine_state.Tt_ideal, ...
                turbine_state.Pt_ideal, ...
                runtime_config.ambient_pressure, ...
                gas, ...
                1.0, ...
                turbine_state.m_dot * (1.0 + turbine_state.fuel_air_ratio_ideal) ...
            );
            [states, nozzle_state] = EngineSim.append_nozzle_state(states, actual_nozzle, ideal_nozzle);
            nozzle_state.Wc = turbine_state.Wc;
            nozzle_state.Wc_ideal = turbine_state.Wc_ideal;
            nozzle_state.Wt = turbine_state.Wt;
            nozzle_state.Wt_ideal = turbine_state.Wt_ideal;
            nozzle_state.Qin = turbine_state.Qin;
            nozzle_state.Qin_ideal = turbine_state.Qin_ideal;
            nozzle_state.fuel_air_ratio = turbine_state.fuel_air_ratio;
            nozzle_state.fuel_air_ratio_ideal = turbine_state.fuel_air_ratio_ideal;

            if turbine_state.Tt <= runtime_config.ambient_temperature
                nozzle_state = EngineSim.mark_infeasible( ...
                    nozzle_state, ...
                    'Turbine exit total temperature fell to ambient or below.' ...
                );
            end
            if turbine_state.Pt <= runtime_config.ambient_pressure
                nozzle_state = EngineSim.add_warning( ...
                    nozzle_state, ...
                    'Turbine exit total pressure is close to ambient, so nozzle thrust is limited.' ...
                );
            end
            nozzle_state = EngineSim.update_state_derived(nozzle_state);
            states(end) = nozzle_state;

            if runtime_config.verbose
                for idx = 2:numel(states)
                    state = states(idx);
                    fprintf('%s: T = %.1f K, P = %.1f kPa, Tt = %.1f K, Pt = %.1f kPa\n', ...
                        state.stage_name, state.T, state.P / 1000.0, state.Tt, state.Pt / 1000.0);
                end
            end

            assumptions = { ...
                'The cycle is modeled as a one-dimensional, steady-flow Brayton cycle.'
                'Air is treated as an ideal gas with constant specific heats.'
                'The compressor and turbine are adiabatic with isentropic efficiencies.'
                'Combustion is represented by heat addition to a target turbine inlet temperature with a pressure loss.'
                'The nozzle is a simple convergent nozzle expanding to ambient or choked conditions.'
            };
            equations = { ...
                'T_t = T + V^2 / (2 c_p)'
                'P_t / P = (T_t / T)^{gamma / (gamma - 1)}'
                'eta_c = (T_{t,2s} - T_{t,1}) / (T_{t,2} - T_{t,1})'
                'eta_t = (T_{t,3} - T_{t,4}) / (T_{t,3} - T_{t,4s})'
                'f = c_p (T_{t,3} - T_{t,2}) / (eta_b * LHV)'
                'F = m_dot_a ((1 + f) V_e - V_0) + (P_e - P_0) A_e'
            };

            result = struct();
            result.states = states;
            result.gas = gas;
            result.config = runtime_config;
            result.assumptions = assumptions;
            result.equations = equations;
            result.extras = struct();
            result.final_state = states(end);
            result.feasible = ~states(end).infeasible;
            result.warnings = states(end).warnings;
            result.station_table = EngineSim.station_table_from_states(states);
            result.component_table = EngineSim.component_table_from_states(states);
        end

        function summary = summarize_result(result, V0)
            if nargin < 2 || isempty(V0)
                V0 = result.config.flight_speed;
            end

            final_state = result.final_state;
            initial_state = result.states(1);
            fuel_flow = final_state.m_dot * final_state.fuel_air_ratio;
            thrust = EngineSim.compute_thrust(final_state, V0);
            jet_power = 0.5 * ((1.0 + final_state.fuel_air_ratio) * final_state.V ^ 2 - V0 ^ 2);

            if final_state.Wt == 0.0
                bwr = 0.0;
            else
                bwr = final_state.Wc / final_state.Wt;
            end

            if final_state.Qin <= 0.0
                shaft_eta = 0.0;
                jet_eta = 0.0;
                overall_eta = 0.0;
            else
                shaft_eta = (final_state.Wt - final_state.Wc) / final_state.Qin;
                jet_eta = jet_power / final_state.Qin;
                overall_eta = thrust * V0 / max(final_state.m_dot * final_state.Qin, EngineSim.MIN_POSITIVE);
            end

            if jet_power <= 0.0
                propulsive_eta = 0.0;
            else
                propulsive_eta = thrust * V0 / max(final_state.m_dot * jet_power, EngineSim.MIN_POSITIVE);
            end

            if fuel_flow <= 0.0
                specific_impulse_s = 0.0;
            else
                specific_impulse_s = thrust / max(fuel_flow * 9.80665, EngineSim.MIN_POSITIVE);
            end

            if final_state.m_dot <= 0.0
                specific_thrust = 0.0;
            else
                specific_thrust = thrust / final_state.m_dot;
            end

            summary = struct();
            summary.thrust_N = thrust;
            summary.specific_thrust_N_per_kg_s = specific_thrust;
            summary.fuel_air_ratio = final_state.fuel_air_ratio;
            summary.fuel_flow_kg_s = fuel_flow;
            summary.specific_impulse_s = specific_impulse_s;
            summary.compressor_work_J_per_kg = final_state.Wc;
            summary.turbine_work_J_per_kg = final_state.Wt;
            summary.net_specific_work_J_per_kg = final_state.Wt - final_state.Wc;
            summary.heat_input_J_per_kg = final_state.Qin;
            summary.bwr = bwr;
            summary.shaft_efficiency = shaft_eta;
            summary.thermal_efficiency = jet_eta;
            summary.jet_power_efficiency = jet_eta;
            summary.propulsive_efficiency = propulsive_eta;
            summary.overall_efficiency = overall_eta;
            summary.exit_velocity_mps = final_state.V;
            summary.exit_mach = final_state.M;
            summary.exit_static_temperature_K = final_state.T;
            summary.exit_total_temperature_K = final_state.Tt;
            summary.exit_static_pressure_Pa = final_state.P;
            summary.exit_total_pressure_Pa = final_state.Pt;
            summary.exit_area_m2 = final_state.exit_area;
            summary.throat_area_m2 = final_state.throat_area;
            summary.pressure_thrust_N = final_state.pressure_thrust;
            summary.nozzle_choked = final_state.nozzle_choked;
            summary.flight_speed_mps = initial_state.V;
            summary.mass_flow_rate_kg_s = final_state.m_dot;
            summary.feasible = ~final_state.infeasible;
            summary.warnings = final_state.warnings;
        end

        function sweep = sweep_parameter(base_config, parameter_name, values)
            if nargin < 3 || isempty(values)
                error('values must contain at least one sweep point.');
            end

            config = EngineSim.prepare_config(base_config);
            parameter_name = char(string(parameter_name));
            values = reshape(double(values), [], 1);
            point_count = numel(values);

            thrust_N = zeros(point_count, 1);
            specific_thrust_N_per_kg_s = zeros(point_count, 1);
            fuel_air_ratio = zeros(point_count, 1);
            fuel_flow_kg_s = zeros(point_count, 1);
            overall_efficiency = zeros(point_count, 1);
            thermal_efficiency = zeros(point_count, 1);
            feasible = false(point_count, 1);

            for idx = 1:point_count
                overrides = struct(parameter_name, values(idx), 'verbose', false);
                if strcmp(parameter_name, 'flight_speed')
                    overrides.flight_input_mode = 'speed';
                end
                case_config = EngineSim.merge_config(config, overrides);
                result = EngineSim.run_engine_case(case_config);
                summary = EngineSim.summarize_result(result, result.config.flight_speed);

                thrust_N(idx) = summary.thrust_N;
                specific_thrust_N_per_kg_s(idx) = summary.specific_thrust_N_per_kg_s;
                fuel_air_ratio(idx) = summary.fuel_air_ratio;
                fuel_flow_kg_s(idx) = summary.fuel_flow_kg_s;
                overall_efficiency(idx) = summary.overall_efficiency;
                thermal_efficiency(idx) = summary.thermal_efficiency;
                feasible(idx) = summary.feasible;
            end

            sweep = table( ...
                values, ...
                thrust_N, ...
                specific_thrust_N_per_kg_s, ...
                fuel_air_ratio, ...
                fuel_flow_kg_s, ...
                overall_efficiency, ...
                thermal_efficiency, ...
                feasible, ...
                'VariableNames', { ...
                    parameter_name, ...
                    'thrust_N', ...
                    'specific_thrust_N_per_kg_s', ...
                    'fuel_air_ratio', ...
                    'fuel_flow_kg_s', ...
                    'overall_efficiency', ...
                    'thermal_efficiency', ...
                    'feasible' ...
                } ...
            );
        end

        function fig = plot_TS(result, show_figure)
            if nargin < 2
                show_figure = true;
            end

            states = result.states;
            actual_s = EngineSim.collect_field(states, 's');
            actual_T = EngineSim.collect_field(states, 'T');
            ideal_s = EngineSim.collect_field(states, 's_ideal');
            ideal_T = EngineSim.collect_field(states, 'T_ideal');

            fig = figure('Name', 'T-s Diagram', 'Visible', EngineSim.visible_value(show_figure));
            ax = axes(fig);
            hold(ax, 'on');
            plot(ax, actual_s, actual_T, '-o', 'LineWidth', 1.6, 'DisplayName', 'Actual');
            plot(ax, ideal_s, ideal_T, '--s', 'LineWidth', 1.4, 'DisplayName', 'Ideal');
            EngineSim.annotate_states(ax, actual_s, actual_T, states);
            xlabel(ax, 'Entropy [J/(kg*K)]');
            ylabel(ax, 'Temperature [K]');
            title(ax, 'Brayton Cycle T-s Diagram');
            legend(ax, 'Location', 'best');
            grid(ax, 'on');
        end

        function fig = plot_PV(result, show_figure)
            if nargin < 2
                show_figure = true;
            end

            states = result.states;
            actual_v = EngineSim.collect_field(states, 'v');
            actual_P = EngineSim.collect_field(states, 'P') / 1000.0;
            ideal_v = EngineSim.collect_field(states, 'v_ideal');
            ideal_P = EngineSim.collect_field(states, 'P_ideal') / 1000.0;

            fig = figure('Name', 'P-v Diagram', 'Visible', EngineSim.visible_value(show_figure));
            ax = axes(fig);
            hold(ax, 'on');
            plot(ax, actual_v, actual_P, '-o', 'LineWidth', 1.6, 'DisplayName', 'Actual');
            plot(ax, ideal_v, ideal_P, '--s', 'LineWidth', 1.4, 'DisplayName', 'Ideal');
            EngineSim.annotate_states(ax, actual_v, actual_P, states);
            xlabel(ax, 'Specific volume [m^3/kg]');
            ylabel(ax, 'Pressure [kPa]');
            title(ax, 'Brayton Cycle P-v Diagram');
            legend(ax, 'Location', 'best');
            grid(ax, 'on');
        end

        function fig = plot_TP(result, show_figure)
            if nargin < 2
                show_figure = true;
            end

            states = result.states;
            actual_T = EngineSim.collect_field(states, 'T');
            actual_P = EngineSim.collect_field(states, 'P') / 1000.0;
            ideal_T = EngineSim.collect_field(states, 'T_ideal');
            ideal_P = EngineSim.collect_field(states, 'P_ideal') / 1000.0;

            fig = figure('Name', 'T-P Diagram', 'Visible', EngineSim.visible_value(show_figure));
            ax = axes(fig);
            hold(ax, 'on');
            plot(ax, actual_T, actual_P, '-o', 'LineWidth', 1.6, 'DisplayName', 'Actual');
            plot(ax, ideal_T, ideal_P, '--s', 'LineWidth', 1.4, 'DisplayName', 'Ideal');
            EngineSim.annotate_states(ax, actual_T, actual_P, states);
            xlabel(ax, 'Temperature [K]');
            ylabel(ax, 'Pressure [kPa]');
            title(ax, 'Brayton Cycle T-P Diagram');
            legend(ax, 'Location', 'best');
            grid(ax, 'on');
        end

        function fig = plot_performance(result, show_figure)
            if nargin < 2
                show_figure = true;
            end

            summary = EngineSim.summarize_result(result, result.config.flight_speed);
            fig = figure('Name', 'Performance Summary', 'Visible', EngineSim.visible_value(show_figure));

            ax1 = subplot(1, 2, 1, 'Parent', fig);
            bar(ax1, categorical({'Thrust', 'Spec thrust', 'Fuel flow', 'Isp'}), ...
                [summary.thrust_N, summary.specific_thrust_N_per_kg_s, summary.fuel_flow_kg_s, summary.specific_impulse_s]);
            ylabel(ax1, 'Magnitude');
            title(ax1, 'Primary Outputs');
            grid(ax1, 'on');

            ax2 = subplot(1, 2, 2, 'Parent', fig);
            bar(ax2, categorical({'Thermal', 'Propulsive', 'Overall', 'BWR'}), ...
                [summary.thermal_efficiency, summary.propulsive_efficiency, summary.overall_efficiency, summary.bwr]);
            ylabel(ax2, 'Magnitude');
            title(ax2, 'Efficiency Metrics');
            grid(ax2, 'on');
        end

        function fig = plot_engine_flow(result, ideal, show_figure)
            if nargin < 2
                ideal = false;
            end
            if nargin < 3
                show_figure = true;
            end

            summary = EngineSim.summarize_result(result, result.config.flight_speed);
            states = result.states;
            fig = figure('Name', 'Engine Flow Schematic', 'Visible', EngineSim.visible_value(show_figure));
            ax = axes(fig);
            hold(ax, 'on');
            axis(ax, [0 1 0 1]);
            axis(ax, 'off');
            title(ax, sprintf('Turbojet Brayton Cycle (%s)', EngineSim.select_label(ideal, 'Ideal', 'Actual')));

            component_names = {'Inlet', 'Compressor', 'Combustor', 'Turbine', 'Nozzle'};
            x_positions = [0.05, 0.23, 0.41, 0.61, 0.80];
            widths = [0.12, 0.14, 0.14, 0.14, 0.12];
            colors = [
                0.80, 0.88, 0.97
                0.74, 0.84, 0.93
                0.99, 0.88, 0.70
                0.86, 0.81, 0.93
                0.79, 0.90, 0.80
            ];

            for idx = 1:numel(component_names)
                rectangle(ax, ...
                    'Position', [x_positions(idx), 0.36, widths(idx), 0.28], ...
                    'FaceColor', colors(idx, :), ...
                    'EdgeColor', [0.15, 0.15, 0.15], ...
                    'LineWidth', 1.2, ...
                    'Curvature', 0.04);
                text(ax, x_positions(idx) + widths(idx) / 2.0, 0.59, component_names{idx}, ...
                    'HorizontalAlignment', 'center', 'FontWeight', 'bold');
                if idx < numel(component_names)
                    line(ax, [x_positions(idx) + widths(idx), x_positions(idx + 1)], [0.50, 0.50], ...
                        'Color', [0.10, 0.10, 0.10], 'LineWidth', 1.5);
                    quiver(ax, x_positions(idx + 1) - 0.015, 0.50, 0.01, 0.0, 0.0, ...
                        'Color', [0.10, 0.10, 0.10], 'LineWidth', 1.5, 'MaxHeadSize', 4.0);
                end
            end

            for idx = 2:numel(states)
                state = states(idx);
                x_center = x_positions(idx - 1) + widths(idx - 1) / 2.0;
                [temp_value, pressure_value] = EngineSim.state_display_values(state, ideal);
                text(ax, x_center, 0.42, sprintf('T%s = %.0f K\nP%s = %.1f kPa', ...
                    EngineSim.select_label(ideal, 't', ''), ...
                    temp_value, ...
                    EngineSim.select_label(ideal, 't', ''), ...
                    pressure_value / 1000.0), ...
                    'HorizontalAlignment', 'center', ...
                    'FontSize', 9);
            end

            text(ax, 0.05, 0.82, sprintf('Flight speed: %.1f m/s', result.config.flight_speed), 'FontWeight', 'bold');
            text(ax, 0.05, 0.76, sprintf('Thrust: %.1f N', summary.thrust_N), 'FontWeight', 'bold');
            text(ax, 0.05, 0.70, sprintf('Fuel-air ratio: %.4f', summary.fuel_air_ratio), 'FontWeight', 'bold');
            text(ax, 0.05, 0.20, sprintf('Nozzle choked: %d', summary.nozzle_choked));
            text(ax, 0.28, 0.20, sprintf('Exit Mach: %.3f', summary.exit_mach));
            text(ax, 0.52, 0.20, sprintf('Overall efficiency: %.4f', summary.overall_efficiency));
        end
    end

    methods (Static, Access = private)
        function config = merge_config(defaults, overrides)
            config = defaults;
            if nargin < 2 || isempty(overrides)
                return;
            end
            if ~isstruct(overrides)
                error('Configuration overrides must be supplied as a struct.');
            end

            override_fields = fieldnames(overrides);
            for idx = 1:numel(override_fields)
                field_name = override_fields{idx};
                if isfield(config, field_name)
                    config.(field_name) = overrides.(field_name);
                end
            end
        end

        function validate_config(config)
            if ~(strcmpi(config.flight_input_mode, 'speed') || strcmpi(config.flight_input_mode, 'mach'))
                error('flight_input_mode must be either ''speed'' or ''mach''.');
            end
            if config.altitude_m < 0.0
                error('altitude_m must be non-negative.');
            end
            if config.flight_speed < 0.0 || config.flight_mach_number < 0.0
                error('flight speed and Mach number must be non-negative.');
            end
            if config.mass_flow_rate <= 0.0
                error('mass_flow_rate must be greater than zero.');
            end
            if config.pressure_recovery <= 0.0 || config.pressure_recovery > 1.0
                error('pressure_recovery must be between 0 and 1.');
            end
            if config.compressor_pressure_ratio < 1.0
                error('compressor_pressure_ratio must be at least 1.');
            end

            limited_fields = { ...
                'compressor_efficiency'
                'combustor_efficiency'
                'turbine_efficiency'
                'mechanical_efficiency'
                'nozzle_efficiency'
            };
            for idx = 1:numel(limited_fields)
                field_name = limited_fields{idx};
                value = config.(field_name);
                if value <= 0.0 || value > 1.0
                    error('%s must be greater than 0 and at most 1.', field_name);
                end
            end

            if config.combustor_pressure_loss < 0.0 || config.combustor_pressure_loss >= 1.0
                error('combustor_pressure_loss must be between 0 and 1.');
            end
            if config.turbine_inlet_temperature <= 0.0
                error('turbine_inlet_temperature must be positive.');
            end
            if config.gas_cp <= 0.0 || config.gas_gamma <= 1.0
                error('gas properties are invalid.');
            end
            if ~isempty(config.gas_R) && config.gas_R <= 0.0
                error('gas_R must be positive when provided.');
            end
            if config.fuel_lower_heating_value <= 0.0
                error('fuel_lower_heating_value must be positive.');
            end
            if config.ambient_temperature <= 0.0 || config.ambient_pressure <= 0.0
                error('ambient conditions must be positive.');
            end
        end

        function gas = build_gas_from_config(config)
            gamma_value = double(config.gas_gamma);
            cp_value = double(config.gas_cp);
            default_r = cp_value * (gamma_value - 1.0) / gamma_value;

            if isempty(config.gas_R)
                gas_constant = default_r;
            else
                gas_constant = double(config.gas_R);
            end

            gas = struct( ...
                'name', char(config.gas_name), ...
                'cp', cp_value, ...
                'gamma', gamma_value, ...
                'R', gas_constant, ...
                'lower_heating_value', double(config.fuel_lower_heating_value), ...
                'burner_efficiency', double(config.combustor_efficiency) ...
            );
        end

        function atmosphere = isa_atmosphere(altitude_m)
            altitude = max(0.0, double(altitude_m));
            g0 = 9.80665;
            troposphere_lapse = 0.0065;
            T0 = 288.15;
            P0 = 101325.0;
            R = 287.05;

            if altitude <= 11000.0
                temperature = T0 - troposphere_lapse * altitude;
                pressure = P0 * (temperature / T0) ^ (g0 / (R * troposphere_lapse));
            else
                temperature = 216.65;
                pressure_11 = P0 * (temperature / T0) ^ (g0 / (R * troposphere_lapse));
                pressure = pressure_11 * exp(-g0 * (altitude - 11000.0) / (R * temperature));
            end

            atmosphere = struct( ...
                'altitude_m', altitude, ...
                'temperature', temperature, ...
                'pressure', pressure, ...
                'density', pressure / (R * temperature) ...
            );
        end

        function state = build_initial_state(config, gas)
            state = EngineSim.make_flow_state( ...
                config.ambient_temperature, ...
                config.ambient_pressure, ...
                config.flight_speed, ...
                config.mass_flow_rate, ...
                0.0, ...
                0.0, ...
                0.0, ...
                gas ...
            );
            state.stage_name = 'Freestream';
        end

        function state = make_flow_state(T, P, V, m_dot, Wc, Wt, Qin, gas)
            state = struct();
            state.gas = gas;
            state.cp = gas.cp;
            state.gamma = gas.gamma;
            state.R = gas.R;

            state.T = double(T);
            state.P = double(P);
            state.V = double(V);
            state.m_dot = double(m_dot);
            state.total_air_mass_flow = double(m_dot);
            state.core_air_mass_flow = double(m_dot);
            state.m_dot_actual = double(m_dot);

            state.s = 0.0;
            state.v = 0.0;
            state.rho = 0.0;
            state.M = 0.0;
            state.area = 0.0;
            state.Tt = double(T);
            state.Pt = double(P);
            state.Wc = double(Wc);
            state.Wt = double(Wt);
            state.Qin = double(Qin);
            state.fuel_air_ratio = 0.0;
            state.pressure_thrust = 0.0;
            state.exit_area = 0.0;
            state.throat_area = 0.0;
            state.nozzle_choked = false;
            state.infeasible = false;
            state.warnings = {};

            state.T_ideal = double(T);
            state.P_ideal = double(P);
            state.V_ideal = double(V);
            state.s_ideal = 0.0;
            state.v_ideal = 0.0;
            state.rho_ideal = 0.0;
            state.M_ideal = 0.0;
            state.area_ideal = 0.0;
            state.Tt_ideal = double(T);
            state.Pt_ideal = double(P);
            state.Wc_ideal = double(Wc);
            state.Wt_ideal = double(Wt);
            state.Qin_ideal = double(Qin);
            state.fuel_air_ratio_ideal = 0.0;
            state.pressure_thrust_ideal = 0.0;
            state.exit_area_ideal = 0.0;
            state.throat_area_ideal = 0.0;
            state.nozzle_choked_ideal = false;

            state.stage_name = '';
            state.stage_index = -1;
            state = EngineSim.update_state_derived(state);
        end

        function [states, state] = append_total_state(states, stage_name, actual_total_temperature, actual_total_pressure, actual_velocity, ideal_total_temperature, ideal_total_pressure, ideal_velocity)
            previous = states(end);
            state = previous;
            state = EngineSim.set_actual_total(state, actual_total_temperature, actual_total_pressure, actual_velocity);
            state = EngineSim.set_ideal_total(state, ideal_total_temperature, ideal_total_pressure, ideal_velocity);
            state.stage_name = char(stage_name);
            state.stage_index = numel(states) - 1;
            state.s = previous.s + EngineSim.entropy_change(state.T, previous.T, state.P, previous.P, state.gas);
            state.s_ideal = previous.s_ideal + ...
                EngineSim.entropy_change(state.T_ideal, previous.T_ideal, state.P_ideal, previous.P_ideal, state.gas);
            state = EngineSim.update_state_derived(state);
            states(end + 1) = state;
        end

        function [states, state] = append_nozzle_state(states, actual_nozzle, ideal_nozzle)
            previous = states(end);
            state = previous;
            state = EngineSim.set_actual_static(state, actual_nozzle.temperature, actual_nozzle.pressure, actual_nozzle.velocity);
            state = EngineSim.set_ideal_static(state, ideal_nozzle.temperature, ideal_nozzle.pressure, ideal_nozzle.velocity);
            state.stage_name = 'Nozzle';
            state.stage_index = numel(states) - 1;
            state.pressure_thrust = actual_nozzle.pressure_thrust;
            state.pressure_thrust_ideal = ideal_nozzle.pressure_thrust;
            state.exit_area = actual_nozzle.exit_area;
            state.exit_area_ideal = ideal_nozzle.exit_area;
            state.throat_area = actual_nozzle.throat_area;
            state.throat_area_ideal = ideal_nozzle.throat_area;
            state.nozzle_choked = actual_nozzle.choked;
            state.nozzle_choked_ideal = ideal_nozzle.choked;
            state.s = previous.s + EngineSim.entropy_change(state.T, previous.T, state.P, previous.P, state.gas);
            state.s_ideal = previous.s_ideal + ...
                EngineSim.entropy_change(state.T_ideal, previous.T_ideal, state.P_ideal, previous.P_ideal, state.gas);
            if ~actual_nozzle.feasible
                state = EngineSim.mark_infeasible(state, actual_nozzle.message);
            end
            state = EngineSim.update_state_derived(state);
            states(end + 1) = state;
        end

        function state = set_actual_static(state, temperature, pressure, velocity)
            state.T = double(temperature);
            state.P = double(pressure);
            state.V = double(velocity);
        end

        function state = set_actual_total(state, temperature_total, pressure_total, velocity)
            static_state = EngineSim.static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, state.gas);
            state.T = static_state.temperature;
            state.P = static_state.pressure;
            state.V = double(velocity);
            state.Tt = double(temperature_total);
            state.Pt = double(pressure_total);
        end

        function state = set_ideal_static(state, temperature, pressure, velocity)
            state.T_ideal = double(temperature);
            state.P_ideal = double(pressure);
            state.V_ideal = double(velocity);
        end

        function state = set_ideal_total(state, temperature_total, pressure_total, velocity)
            static_state = EngineSim.static_state_from_total_and_velocity(temperature_total, pressure_total, velocity, state.gas);
            state.T_ideal = static_state.temperature;
            state.P_ideal = static_state.pressure;
            state.V_ideal = double(velocity);
            state.Tt_ideal = double(temperature_total);
            state.Pt_ideal = double(pressure_total);
        end

        function state = add_warning(state, message)
            if isempty(message)
                return;
            end

            message = char(message);
            if isempty(state.warnings)
                state.warnings = {message};
                return;
            end

            if ~any(strcmp(state.warnings, message))
                state.warnings{end + 1} = message;
            end
        end

        function state = mark_infeasible(state, message)
            state.infeasible = true;
            state = EngineSim.add_warning(state, message);
        end

        function message = status_message(state)
            if isempty(state.warnings)
                message = '';
            else
                message = strjoin(state.warnings, ' | ');
            end
        end

        function state = update_state_derived(state)
            state.cp = state.gas.cp;
            state.gamma = state.gas.gamma;
            state.R = state.gas.R;
            state.core_air_mass_flow = state.m_dot;
            state.m_dot_actual = state.m_dot * (1.0 + state.fuel_air_ratio);

            state.v = EngineSim.specific_volume(state.T, state.P, state.R);
            state.rho = EngineSim.density(state.T, state.P, state.R);
            state.M = EngineSim.mach_number(state.V, state.T, state.gas);
            stagnation_actual = EngineSim.stagnation_state_from_static(state.T, state.P, state.V, state.gas);
            state.Tt = stagnation_actual.temperature;
            state.Pt = stagnation_actual.pressure;
            if state.V > EngineSim.MIN_POSITIVE
                state.area = EngineSim.flow_area(state.m_dot_actual, state.rho, state.V);
            else
                state.area = 0.0;
            end

            state.v_ideal = EngineSim.specific_volume(state.T_ideal, state.P_ideal, state.R);
            state.rho_ideal = EngineSim.density(state.T_ideal, state.P_ideal, state.R);
            state.M_ideal = EngineSim.mach_number(state.V_ideal, state.T_ideal, state.gas);
            stagnation_ideal = EngineSim.stagnation_state_from_static(state.T_ideal, state.P_ideal, state.V_ideal, state.gas);
            state.Tt_ideal = stagnation_ideal.temperature;
            state.Pt_ideal = stagnation_ideal.pressure;
            ideal_mass_flow = state.m_dot * (1.0 + state.fuel_air_ratio_ideal);
            if state.V_ideal > EngineSim.MIN_POSITIVE
                state.area_ideal = EngineSim.flow_area(ideal_mass_flow, state.rho_ideal, state.V_ideal);
            else
                state.area_ideal = 0.0;
            end
        end

        function value = m_dot_actual(state)
            value = state.m_dot * (1.0 + state.fuel_air_ratio);
        end

        function tbl = station_table_from_states(states)
            count = numel(states);

            stage_name = strings(count, 1);
            stage_index = zeros(count, 1);
            actual_static_temperature_K = zeros(count, 1);
            actual_total_temperature_K = zeros(count, 1);
            actual_static_pressure_kPa = zeros(count, 1);
            actual_total_pressure_kPa = zeros(count, 1);
            actual_velocity_mps = zeros(count, 1);
            actual_entropy_J_per_kgK = zeros(count, 1);
            actual_specific_volume_m3_per_kg = zeros(count, 1);
            actual_density_kg_per_m3 = zeros(count, 1);
            actual_mach = zeros(count, 1);
            actual_area_m2 = zeros(count, 1);
            ideal_static_temperature_K = zeros(count, 1);
            ideal_total_temperature_K = zeros(count, 1);
            ideal_static_pressure_kPa = zeros(count, 1);
            ideal_total_pressure_kPa = zeros(count, 1);
            ideal_velocity_mps = zeros(count, 1);
            ideal_entropy_J_per_kgK = zeros(count, 1);
            ideal_specific_volume_m3_per_kg = zeros(count, 1);
            ideal_density_kg_per_m3 = zeros(count, 1);
            ideal_mach = zeros(count, 1);
            ideal_area_m2 = zeros(count, 1);
            cumulative_fuel_air_ratio = zeros(count, 1);
            heat_input_J_per_kg_air = zeros(count, 1);
            compressor_work_J_per_kg_air = zeros(count, 1);
            turbine_work_J_per_kg_air = zeros(count, 1);
            pressure_thrust_N = zeros(count, 1);
            nozzle_choked = false(count, 1);
            mass_flow_rate_kg_s = zeros(count, 1);
            infeasible = false(count, 1);
            status_message = strings(count, 1);

            for idx = 1:count
                state = states(idx);
                stage_name(idx) = string(EngineSim.default_stage_name(state.stage_name));
                stage_index(idx) = state.stage_index;
                actual_static_temperature_K(idx) = state.T;
                actual_total_temperature_K(idx) = state.Tt;
                actual_static_pressure_kPa(idx) = state.P / 1000.0;
                actual_total_pressure_kPa(idx) = state.Pt / 1000.0;
                actual_velocity_mps(idx) = state.V;
                actual_entropy_J_per_kgK(idx) = state.s;
                actual_specific_volume_m3_per_kg(idx) = state.v;
                actual_density_kg_per_m3(idx) = state.rho;
                actual_mach(idx) = state.M;
                actual_area_m2(idx) = state.area;
                ideal_static_temperature_K(idx) = state.T_ideal;
                ideal_total_temperature_K(idx) = state.Tt_ideal;
                ideal_static_pressure_kPa(idx) = state.P_ideal / 1000.0;
                ideal_total_pressure_kPa(idx) = state.Pt_ideal / 1000.0;
                ideal_velocity_mps(idx) = state.V_ideal;
                ideal_entropy_J_per_kgK(idx) = state.s_ideal;
                ideal_specific_volume_m3_per_kg(idx) = state.v_ideal;
                ideal_density_kg_per_m3(idx) = state.rho_ideal;
                ideal_mach(idx) = state.M_ideal;
                ideal_area_m2(idx) = state.area_ideal;
                cumulative_fuel_air_ratio(idx) = state.fuel_air_ratio;
                heat_input_J_per_kg_air(idx) = state.Qin;
                compressor_work_J_per_kg_air(idx) = state.Wc;
                turbine_work_J_per_kg_air(idx) = state.Wt;
                pressure_thrust_N(idx) = state.pressure_thrust;
                nozzle_choked(idx) = state.nozzle_choked;
                mass_flow_rate_kg_s(idx) = state.m_dot;
                infeasible(idx) = state.infeasible;
                status_message(idx) = string(EngineSim.status_message(state));
            end

            tbl = table( ...
                stage_name, ...
                stage_index, ...
                actual_static_temperature_K, ...
                actual_total_temperature_K, ...
                actual_static_pressure_kPa, ...
                actual_total_pressure_kPa, ...
                actual_velocity_mps, ...
                actual_entropy_J_per_kgK, ...
                actual_specific_volume_m3_per_kg, ...
                actual_density_kg_per_m3, ...
                actual_mach, ...
                actual_area_m2, ...
                ideal_static_temperature_K, ...
                ideal_total_temperature_K, ...
                ideal_static_pressure_kPa, ...
                ideal_total_pressure_kPa, ...
                ideal_velocity_mps, ...
                ideal_entropy_J_per_kgK, ...
                ideal_specific_volume_m3_per_kg, ...
                ideal_density_kg_per_m3, ...
                ideal_mach, ...
                ideal_area_m2, ...
                cumulative_fuel_air_ratio, ...
                heat_input_J_per_kg_air, ...
                compressor_work_J_per_kg_air, ...
                turbine_work_J_per_kg_air, ...
                pressure_thrust_N, ...
                nozzle_choked, ...
                mass_flow_rate_kg_s, ...
                infeasible, ...
                status_message ...
            );

            tbl.Properties.VariableNames = { ...
                'stage_name', ...
                'stage_index', ...
                'actual_static_temperature_K', ...
                'actual_total_temperature_K', ...
                'actual_static_pressure_kPa', ...
                'actual_total_pressure_kPa', ...
                'actual_velocity_mps', ...
                'actual_entropy_J_per_kgK', ...
                'actual_specific_volume_m3_per_kg', ...
                'actual_density_kg_per_m3', ...
                'actual_mach', ...
                'actual_area_m2', ...
                'ideal_static_temperature_K', ...
                'ideal_total_temperature_K', ...
                'ideal_static_pressure_kPa', ...
                'ideal_total_pressure_kPa', ...
                'ideal_velocity_mps', ...
                'ideal_entropy_J_per_kgK', ...
                'ideal_specific_volume_m3_per_kg', ...
                'ideal_density_kg_per_m3', ...
                'ideal_mach', ...
                'ideal_area_m2', ...
                'cumulative_fuel_air_ratio', ...
                'heat_input_J_per_kg_air', ...
                'compressor_work_J_per_kg_air', ...
                'turbine_work_J_per_kg_air', ...
                'pressure_thrust_N', ...
                'nozzle_choked', ...
                'mass_flow_rate_kg_s', ...
                'infeasible', ...
                'status_message' ...
            };
            tbl.fuel_air_ratio = tbl.cumulative_fuel_air_ratio;
            tbl.actual_temperature_K = tbl.actual_static_temperature_K;
            tbl.actual_pressure_kPa = tbl.actual_static_pressure_kPa;
            tbl.ideal_temperature_K = tbl.ideal_static_temperature_K;
            tbl.ideal_pressure_kPa = tbl.ideal_static_pressure_kPa;
        end

        function tbl = component_table_from_states(states)
            count = numel(states);
            row_count = max(count - 1, 0);

            stage_name = strings(row_count, 1);
            actual_delta_total_temperature_K = zeros(row_count, 1);
            actual_total_pressure_ratio = zeros(row_count, 1);
            actual_delta_velocity_mps = zeros(row_count, 1);
            ideal_delta_total_temperature_K = zeros(row_count, 1);
            ideal_total_pressure_ratio = zeros(row_count, 1);
            ideal_delta_velocity_mps = zeros(row_count, 1);
            delta_heat_input_J_per_kg_air = zeros(row_count, 1);
            delta_compressor_work_J_per_kg_air = zeros(row_count, 1);
            delta_turbine_work_J_per_kg_air = zeros(row_count, 1);

            for idx = 2:count
                inlet = states(idx - 1);
                outlet = states(idx);
                row = idx - 1;
                stage_name(row) = string(EngineSim.default_stage_name(outlet.stage_name));
                actual_delta_total_temperature_K(row) = outlet.Tt - inlet.Tt;
                ideal_delta_total_temperature_K(row) = outlet.Tt_ideal - inlet.Tt_ideal;
                actual_delta_velocity_mps(row) = outlet.V - inlet.V;
                ideal_delta_velocity_mps(row) = outlet.V_ideal - inlet.V_ideal;
                delta_heat_input_J_per_kg_air(row) = outlet.Qin - inlet.Qin;
                delta_compressor_work_J_per_kg_air(row) = outlet.Wc - inlet.Wc;
                delta_turbine_work_J_per_kg_air(row) = outlet.Wt - inlet.Wt;
                if inlet.Pt == 0.0
                    actual_total_pressure_ratio(row) = 0.0;
                else
                    actual_total_pressure_ratio(row) = outlet.Pt / inlet.Pt;
                end
                if inlet.Pt_ideal == 0.0
                    ideal_total_pressure_ratio(row) = 0.0;
                else
                    ideal_total_pressure_ratio(row) = outlet.Pt_ideal / inlet.Pt_ideal;
                end
            end

            tbl = table( ...
                stage_name, ...
                actual_delta_total_temperature_K, ...
                actual_total_pressure_ratio, ...
                actual_delta_velocity_mps, ...
                ideal_delta_total_temperature_K, ...
                ideal_total_pressure_ratio, ...
                ideal_delta_velocity_mps, ...
                delta_heat_input_J_per_kg_air, ...
                delta_compressor_work_J_per_kg_air, ...
                delta_turbine_work_J_per_kg_air ...
            );
            tbl.Properties.VariableNames = { ...
                'stage_name', ...
                'actual_delta_total_temperature_K', ...
                'actual_total_pressure_ratio', ...
                'actual_delta_velocity_mps', ...
                'ideal_delta_total_temperature_K', ...
                'ideal_total_pressure_ratio', ...
                'ideal_delta_velocity_mps', ...
                'delta_heat_input_J_per_kg_air', ...
                'delta_compressor_work_J_per_kg_air', ...
                'delta_turbine_work_J_per_kg_air' ...
            };
        end

        function thrust = compute_thrust(state, V0)
            m_dot_exit = state.m_dot * (1.0 + state.fuel_air_ratio);
            momentum_thrust = m_dot_exit * state.V - state.m_dot * V0;
            thrust = momentum_thrust + state.pressure_thrust;
        end

        function value = specific_volume(T, P, gas_constant)
            value = gas_constant * T / max(P, EngineSim.MIN_POSITIVE);
        end

        function value = density(T, P, gas_constant)
            value = P / max(gas_constant * T, EngineSim.MIN_POSITIVE);
        end

        function value = speed_of_sound(T, gas)
            value = sqrt(max(EngineSim.MIN_POSITIVE, gas.gamma * gas.R * T));
        end

        function value = mach_number(velocity, T, gas)
            value = velocity / max(EngineSim.speed_of_sound(T, gas), EngineSim.MIN_POSITIVE);
        end

        function value = total_temperature(T, velocity, gas)
            value = T + velocity ^ 2 / (2.0 * gas.cp);
        end

        function value = static_temperature_from_total(T_total, velocity, gas)
            value = max(1.0, T_total - velocity ^ 2 / (2.0 * gas.cp));
        end

        function value = stagnation_pressure_from_static(T_static, P_static, T_total, gas)
            exponent = gas.gamma / (gas.gamma - 1.0);
            value = P_static * (T_total / max(T_static, EngineSim.MIN_POSITIVE)) ^ exponent;
        end

        function value = static_pressure_from_stagnation(T_static, T_total, P_total, gas)
            exponent = gas.gamma / (gas.gamma - 1.0);
            value = P_total * (T_static / max(T_total, EngineSim.MIN_POSITIVE)) ^ exponent;
        end

        function static_state = static_state_from_total_and_velocity(T_total, P_total, velocity, gas)
            T_static = EngineSim.static_temperature_from_total(T_total, velocity, gas);
            P_static = EngineSim.static_pressure_from_stagnation(T_static, T_total, P_total, gas);
            static_state = struct( ...
                'temperature', T_static, ...
                'pressure', P_static, ...
                'density', EngineSim.density(T_static, P_static, gas.R), ...
                'specific_volume', EngineSim.specific_volume(T_static, P_static, gas.R), ...
                'mach', EngineSim.mach_number(velocity, T_static, gas) ...
            );
        end

        function total_state = stagnation_state_from_static(T_static, P_static, velocity, gas)
            T_total = EngineSim.total_temperature(T_static, velocity, gas);
            P_total = EngineSim.stagnation_pressure_from_static(T_static, P_static, T_total, gas);
            total_state = struct( ...
                'temperature', T_total, ...
                'pressure', P_total, ...
                'mach', EngineSim.mach_number(velocity, T_static, gas) ...
            );
        end

        function value = entropy_change(T2, T1, P2, P1, gas)
            value = gas.cp * log(max(T2, EngineSim.MIN_POSITIVE) / max(T1, EngineSim.MIN_POSITIVE)) ...
                - gas.R * log(max(P2, EngineSim.MIN_POSITIVE) / max(P1, EngineSim.MIN_POSITIVE));
        end

        function value = isentropic_temperature(T_in, P_out, P_in, gas)
            exponent = (gas.gamma - 1.0) / gas.gamma;
            value = max(1.0, T_in * (P_out / max(P_in, EngineSim.MIN_POSITIVE)) ^ exponent);
        end

        function value = critical_pressure_ratio(gas)
            gamma_value = gas.gamma;
            value = (2.0 / (gamma_value + 1.0)) ^ (gamma_value / (gamma_value - 1.0));
        end

        function value = flow_area(m_dot, rho, velocity)
            if m_dot <= 0.0 || rho <= 0.0 || velocity <= EngineSim.MIN_POSITIVE
                value = NaN;
                return;
            end
            value = m_dot / (rho * velocity);
        end

        function nozzle_state = nozzle_exit_state(T_total, P_total, ambient_pressure, gas, eta_n, m_dot)
            if T_total <= 0.0 || P_total <= 0.0 || ambient_pressure <= 0.0 || m_dot <= 0.0
                nozzle_state = struct( ...
                    'temperature', NaN, ...
                    'pressure', NaN, ...
                    'velocity', 0.0, ...
                    'density', NaN, ...
                    'mach', NaN, ...
                    'exit_area', NaN, ...
                    'throat_area', NaN, ...
                    'pressure_thrust', 0.0, ...
                    'choked', false, ...
                    'feasible', false, ...
                    'message', 'Nozzle inlet conditions are not physical.' ...
                );
                return;
            end

            critical_pressure = P_total * EngineSim.critical_pressure_ratio(gas);
            choked = ambient_pressure <= critical_pressure;
            if choked
                exit_pressure = critical_pressure;
            else
                exit_pressure = ambient_pressure;
            end

            T_exit_isentropic = EngineSim.isentropic_temperature(T_total, exit_pressure, P_total, gas);
            T_exit = T_total - eta_n * (T_total - T_exit_isentropic);
            T_exit = max(1.0, min(T_exit, T_total));
            exit_velocity = sqrt(max(0.0, 2.0 * gas.cp * (T_total - T_exit)));
            exit_density = EngineSim.density(T_exit, exit_pressure, gas.R);
            exit_area = EngineSim.flow_area(m_dot, exit_density, exit_velocity);

            T_star = 2.0 * T_total / (gas.gamma + 1.0);
            P_star = critical_pressure;
            rho_star = EngineSim.density(T_star, P_star, gas.R);
            a_star = EngineSim.speed_of_sound(T_star, gas);
            if choked
                throat_area = EngineSim.flow_area(m_dot, rho_star, a_star);
            else
                throat_area = exit_area;
            end

            feasible = isfinite(exit_area) && exit_velocity > 0.0;
            if feasible
                pressure_thrust = (exit_pressure - ambient_pressure) * exit_area;
                message = '';
            else
                pressure_thrust = 0.0;
                message = 'Nozzle expansion produced a non-physical exit condition.';
            end

            nozzle_state = struct( ...
                'temperature', T_exit, ...
                'pressure', exit_pressure, ...
                'velocity', exit_velocity, ...
                'density', exit_density, ...
                'mach', EngineSim.mach_number(exit_velocity, T_exit, gas), ...
                'exit_area', exit_area, ...
                'throat_area', throat_area, ...
                'pressure_thrust', pressure_thrust, ...
                'choked', choked, ...
                'feasible', feasible, ...
                'message', message ...
            );
        end

        function labels = collect_stage_names(states)
            count = numel(states);
            labels = cell(count, 1);
            for idx = 1:count
                labels{idx} = EngineSim.default_stage_name(states(idx).stage_name);
            end
        end

        function values = collect_field(states, field_name)
            count = numel(states);
            values = zeros(count, 1);
            for idx = 1:count
                values(idx) = states(idx).(field_name);
            end
        end

        function annotate_states(ax, x_values, y_values, states)
            labels = EngineSim.collect_stage_names(states);
            for idx = 1:numel(labels)
                text(ax, x_values(idx), y_values(idx), ['  ' labels{idx}], ...
                    'FontSize', 8, 'VerticalAlignment', 'bottom');
            end
        end

        function [temperature, pressure] = state_display_values(state, ideal)
            if ideal
                temperature = state.Tt_ideal;
                pressure = state.Pt_ideal;
            else
                temperature = state.Tt;
                pressure = state.Pt;
            end
        end

        function label = default_stage_name(stage_name)
            if isempty(stage_name)
                label = 'Freestream';
            else
                label = stage_name;
            end
        end

        function label = select_label(condition, true_label, false_label)
            if condition
                label = true_label;
            else
                label = false_label;
            end
        end

        function visible = visible_value(show_figure)
            if show_figure
                visible = 'on';
            else
                visible = 'off';
            end
        end

        function output_dir = export_main_outputs(result, summary, figures, figure_names)
            class_path = which('EngineSim');
            matlab_dir = fileparts(class_path);
            root_dir = fileparts(matlab_dir);
            output_dir = fullfile(root_dir, 'outputs', 'matlab');
            if ~exist(output_dir, 'dir')
                mkdir(output_dir);
            end

            for idx = 1:numel(figures)
                exportgraphics(figures{idx}, fullfile(output_dir, [figure_names{idx} '.png']));
            end

            writetable(result.station_table, fullfile(output_dir, 'station_table.csv'));
            writetable(result.component_table, fullfile(output_dir, 'component_table.csv'));

            summary_export = rmfield(summary, 'warnings');
            summary_export.warning_text = strjoin(summary.warnings, ' | ');
            writetable(struct2table(summary_export), fullfile(output_dir, 'summary.csv'));
        end
    end
end
