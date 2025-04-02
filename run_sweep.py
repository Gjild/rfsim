#!/usr/bin/env python
import argparse
import yaml
import logging
from typing import Optional
from utils.logging_config import setup_logging, get_logger
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep
from core.exceptions import RFSimError

logger = get_logger(__name__)

def main() -> None:
    """
    Run an RF circuit sweep simulation based on YAML configuration files.
    
    Command-line arguments:
      --netlist: Path to the YAML netlist file.
      --sweep: Path to the YAML sweep configuration file.
      --dump: Optional path to dump sweep results (e.g., sweep.npz).
      --summary: Print a summary of the sweep results.
      --verbose: Enable DEBUG logging.
    """
    parser = argparse.ArgumentParser(description="Run an RF circuit sweep simulation.")
    parser.add_argument("--netlist", required=True, help="Path to the YAML netlist file.")
    parser.add_argument("--sweep", required=True, help="Path to the YAML sweep configuration file.")
    parser.add_argument("--dump", help="Path to dump sweep result (e.g., sweep.npz)", default=None)
    parser.add_argument("--summary", action="store_true", help="Print sweep summary.")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    args = parser.parse_args()

    if args.verbose:
        setup_logging(level=logging.DEBUG)
        logger.debug("Verbose logging enabled.")
    else:
        setup_logging(level=logging.INFO)

    try:
        circuit = parse_netlist(args.netlist)
        circuit.validate(verbose=True)
    except RFSimError as e:
        logger.error("Circuit validation failed: %s", e)
        return

    with open(args.sweep, 'r') as f:
        sweep_config = yaml.safe_load(f)

    result = sweep(circuit, sweep_config)
    logger.info("Sweep completed.")

    if result.errors:
        logger.warning("Some errors occurred during the sweep:")
        for err in result.errors:
            logger.warning(err)
    else:
        logger.info("No errors reported during the sweep.")

    if args.summary:
        print(f"Sweep completed: {result.stats['points']} points in {result.stats['elapsed']:.3f} s")

    if args.dump:
        import numpy as np
        freqs = []
        smatrices = []
        params_list = []
        for (freq, param_tuple), S in result.results.items():
            freqs.append(freq)
            smatrices.append(S)
            params_list.append(dict(param_tuple))
        np.savez(args.dump, freqs=freqs, smatrices=smatrices, params=params_list)
        print(f"Sweep results dumped to {args.dump}")

    for key in result.results:
        print(f"Point: {key} -> S-matrix shape: {result.results[key].shape}")

if __name__ == "__main__":
    main()
