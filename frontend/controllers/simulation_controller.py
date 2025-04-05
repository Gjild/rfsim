# frontend/controllers/simulation_controller.py
import os
import time
import threading
from ruamel.yaml import YAML
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep

from frontend.models.state import StateManager
from frontend.utils.expr_eval import hash_file

class SimulationController:
    """
    Controls the simulation process.
    """
    def __init__(self, state: StateManager, ui_callback_update: callable) -> None:
        self.state = state
        self.ui_callback_update = ui_callback_update  # Callback to update UI elements.
        self.yaml_parser = YAML()

    def run_simulation(self) -> None:
        self.state.simulation_results = None
        self.state.simulation_status.running = True
        self.state.simulation_status.progress = 0.0
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

            # Trigger UI update callback to refresh plots.
            self.ui_callback_update()
        except Exception as e:
            self.state.add_log("Simulation failed: " + str(e))
        finally:
            self.state.simulation_status.running = False
            self.state.simulation_status.progress = 1.0
            time.sleep(0.2)  # Allow UI to process final updates

    def start(self) -> None:
        if self.state.simulation_status.running:
            self.state.add_log("Simulation is already running.")
            return
        sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
        sim_thread.start()
