import numpy as np
from concurrent.futures import ProcessPoolExecutor
import itertools
import logging
import time

# NEW: Top-level helper so it can be pickled.
def _evaluate_point(circuit, freq, param_values, keys):
    local_params = {keys[i]: param_values[i] for i in range(len(keys))}
    try:
        res = circuit.evaluate(freq, local_params)
        return (freq, local_params, res.s_matrix)
    except Exception as e:
        # Log the error with detailed context.
        logging.error(f"Error at frequency {freq:.3e} Hz with parameters {local_params}: {e}")
        # Return an error tuple so that the sweep engine can collect and report it separately.
        return (freq, local_params, None, str(e))

class SweepResult:
    """
    Encapsulates sweep results and basic statistics.
    """
    def __init__(self, results, errors, stats=None):
        self.results = results
        self.errors = errors
        self.stats = stats if stats is not None else {}

    def to_dataframe(self):
        import pandas as pd
        rows = []
        for (freq, params_tuple), s_matrix in self.results.items():
            key_freq = round(freq, 9)
            row = {"frequency": key_freq}
            row.update(dict(params_tuple))
            row["s_matrix"] = s_matrix
            rows.append(row)
        return pd.DataFrame(rows)

def sweep(circuit, config):
    sweep_list = config.get("sweep", [])
    freq_sweep = None
    param_sweeps = {}
    for s in sweep_list:
        param = s.get("param")
        if param == "f":
            start, end = map(float, s.get("range"))
            points = s.get("points")
            scale = s.get("scale", "linear")
            if scale == "log":
                freq_sweep = np.logspace(np.log10(start), np.log10(end), points)
            else:
                freq_sweep = np.linspace(start, end, points)
        else:
            param_sweeps[param] = s.get("values")
    keys = list(param_sweeps.keys())
    values_product = list(itertools.product(*param_sweeps.values())) if param_sweeps else [()]
    results = {}
    errors = []
    start_time = time.time()

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(_evaluate_point, circuit, freq, param_vals, keys)
                   for freq, param_vals in [(freq, param_vals) for freq in freq_sweep for param_vals in values_product]]
        for future in futures:
            result = future.result()
            if len(result) == 4:
                # Append error information without mixing with valid S-matrix data.
                errors.append(f"Frequency {result[0]:.3e} Hz, Params {result[1]}: {result[-1]}")
            else:
                freq, local_params, s_matrix = result
                key = (round(freq, 9), tuple(sorted(local_params.items())))
                results[key] = s_matrix
    elapsed = time.time() - start_time
    stats = {"points": len(freq_sweep) * len(values_product), "elapsed": elapsed}
    return SweepResult(results, errors, stats)
