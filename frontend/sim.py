# frontend/sim.py
import os
import time
import threading
from ruamel.yaml import YAML
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep

from frontend.states import StateManager
from utils.expr_eval import hash_file

class SimulationController:
    """
    Controls the simulation process including input file loading, running
    the sweep, and triggering UI updates.
    """
    def __init__(self, state: StateManager, ui_controller: 'UIController') -> None:
        self.state = state
        self.ui_controller = ui_controller
        self.yaml_parser = YAML()

    def run_simulation(self) -> None:
        self.state.simulation_results = None
        self.state.simulation_running = True
        self.state.simulation_progress = 0.0
        self.state.add_log("Simulation started.")
        try:
            if not os.path.exists(self.state.netlist_path):
                raise FileNotFoundError(f"Netlist file not found: {self.state.netlist_path}")
            if not os.path.exists(self.state.sweep_config_path):
                raise FileNotFoundError(f"Sweep config file not found: {self.state.sweep_config_path}")

            if not self.state.needs_simulation(hash_file):
                self.state.add_log("Input files unchanged, skipping re-simulation.")
                return

            self.state.add_log("Loading netlist...")
            circuit = parse_netlist(self.state.netlist_path)
            circuit.validate(verbose=True)
            self.state.add_log("Netlist loaded and validated.")

            self.state.add_log("Loading sweep configuration...")
            with open(self.state.sweep_config_path, 'r') as f:
                sweep_config_data = self.yaml_parser.load(f)
            self.state.add_log("Sweep configuration loaded.")

            self.state.add_log("Running simulation sweep...")
            result = sweep(circuit, sweep_config_data)
            self.state.simulation_results = result
            self.state.add_log("Simulation completed successfully.")

            # Update plots based on their type.
            for plot_id, plot_tab in self.state.plot_tabs.items():
                if plot_tab.type == "rectangular":
                    self.ui_controller.plot_manager.update_rectangular_plot(plot_id)
                elif plot_tab.type == "smith":
                    self.ui_controller.plot_manager.update_smith_chart(plot_id)
        except Exception as e:
            self.state.add_log("Simulation failed: " + str(e))
        finally:
            self.state.simulation_running = False
            self.state.simulation_progress = 1.0
            time.sleep(0.2)  # Allow UI updates to process

    def start(self) -> None:
        sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
        sim_thread.start()
