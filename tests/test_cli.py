import subprocess
import sys
import os

def test_cli_smoke(tmp_path):
    # Create a minimal netlist YAML.
    netlist = {
        "components": [
            {"id": "R1", "type": "resistor", "params": {"R": "1000"}, "ports": ["1", "2"]}
        ],
        "connections": [
            {"port": "R1.1", "node": "n1"},
            {"port": "R1.2", "node": "n2"}
        ]
    }
    netlist_file = tmp_path / "netlist.yml"
    with open(netlist_file, "w") as f:
        import yaml
        yaml.dump(netlist, f)

    # Create a minimal sweep configuration.
    sweep_config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6], "points": 1, "scale": "linear"}
        ]
    }
    sweep_file = tmp_path / "sweep.yml"
    with open(sweep_file, "w") as f:
        import yaml
        yaml.dump(sweep_config, f)

    # Run the CLI.
    cmd = [sys.executable, "run_sweep.py", "--netlist", str(netlist_file), "--sweep", str(sweep_file)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Combine stdout and stderr for the check.
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert "Sweep completed" in output
