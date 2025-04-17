# core/simulator.py
"""
Simulator entry point for RFSim v2.
Handles loading netlists, running sweeps, and configuration of numeric backends.
"""
import argparse
from pathlib import Path

from core.inout.netlist import load_netlist
from core.inout.sweep import load_sweep_config
from core.topology.netlist_graph import NetlistGraph
from core.stamping.matrix_builder import MatrixBuilder
from core.parameters.resolver import resolve as resolve_parameters
from core.exceptions import RFSimError
from core.validation import validate_circuit_structure


class Simulator:
    def __init__(self, sparse: bool = True, tol: float = 1e-9):
        # Numeric configuration
        self.sparse = sparse
        self.tol = tol

    def load_netlist(self, path: Path):
        """
        Load a YAML netlist file and return a CircuitModel.
        Raises RFSimError on validation errors.
        """
        return load_netlist(path)

    def run_sweep(self, circuit, sweep_config: dict):
        """
        Run a parameter/frequency sweep on the given circuit model.
        Returns a SweepResult.
        """
        # Resolve global parameters
        try:
            resolved_globals = resolve_parameters(circuit.global_parameters)
        except Exception as e:
            raise RFSimError(f"Parameter resolution failed: {e}")

        # Build topology graph
        graph = NetlistGraph.from_circuit(circuit)

        # Prepare MatrixBuilder
        matrix_builder = MatrixBuilder(graph, circuit, tol=self.tol, sparse=self.sparse)
        static_pkg = matrix_builder.export_static() 

        # Execute sweep
        return matrix_builder.sweep(circuit, sweep_config, resolved_globals)


def main():
    parser = argparse.ArgumentParser(description="RFSim v2.0 Simulation Runner")
    parser.add_argument("--netlist", type=Path, required=True, help="Path to YAML netlist file")
    parser.add_argument("--sweep", type=Path, required=True, help="Path to sweep config file")
    parser.add_argument("--output", type=Path, help="Optional output file for results")
    parser.add_argument("--sparse", action="store_true", help="Use sparse matrix backend (default)")
    parser.add_argument("--dense", dest="sparse", action="store_false", help="Use dense matrix backend")
    parser.add_argument("--tol", type=float, default=1e-9, help="Numeric tolerance for matrix operations")
    args = parser.parse_args()

    sim = Simulator(sparse=args.sparse, tol=args.tol)
    try:
        circuit = sim.load_netlist(args.netlist)
        validate_circuit_structure(circuit)
    except RFSimError as e:
        print(f"Netlist load failed: {e}")
        return

    try:
        sweep_cfg = load_sweep_config(args.sweep)
        result = sim.run_sweep(circuit, sweep_cfg)
    except RFSimError as e:
        print(f"Sweep configuration or execution error: {e}")
        return

    # TODO: serialize and output result
    print("Sweep completed. Results entries:")
    for entry in result.entries:
        print(entry)
    if result.errors:
        print("Errors:")
        for err in result.errors:
            print(err)


if __name__ == "__main__":
    main()
