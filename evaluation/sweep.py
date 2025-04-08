# evaluation/sweep.py
import numpy as np
import itertools
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from core.evaluation_types import EvaluationPoint
from core.exceptions import ComponentEvaluationError

# Top-level helper for evaluation.
def _evaluate_point(circuit, freq, param_values, keys) -> EvaluationPoint:
    local_params = {keys[i]: param_values[i] for i in range(len(keys))}
    try:
        res = circuit.evaluate(freq, local_params)
        return EvaluationPoint(
            frequency=freq,
            parameters=local_params,
            s_matrix=res.s_matrix,  # You can still keep this for backward compatibility or convenience.
            evaluation_result=res  # NEW: full evaluation context!
        )
    except Exception as e:
        logging.error(f"Error at frequency {freq:.3e} Hz with parameters {local_params}: {e}")
        return EvaluationPoint(frequency=freq, parameters=local_params, error=str(e))
    

def evaluate_batch(circuit, batch_points, keys):
    """
    Evaluate a batch of sweep points.
    """
    batch_results = []
    for freq, param_vals in batch_points:
        point = _evaluate_point(circuit, freq, param_vals, keys)
        batch_results.append(point)
    return batch_results
    
class SweepResult:
    def __init__(self, results, errors, stats=None):
        self.results = results
        self.errors = errors
        self.stats = stats if stats is not None else {}

    def to_dataframe(self):
        import pandas as pd
        rows = []
        for (freq, params_tuple), eval_result in self.results.items():
            key_freq = round(freq, 9)
            row = {"frequency": key_freq}
            row.update(dict(params_tuple))
            if eval_result is not None:
                row["s_matrix"] = eval_result.s_matrix
                row["port_order"] = eval_result.port_order
                row["node_mapping"] = eval_result.node_mapping
                row["stats"] = eval_result.stats
            else:
                row["s_matrix"] = None
                row["port_order"] = None
                row["node_mapping"] = None
                row["stats"] = None
            rows.append(row)
        return pd.DataFrame(rows)


def sweep(circuit, config):
    """
    Run the sweep simulation by evaluating batches of sweep points in parallel.
    """
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
    sweep_points = [(freq, param_vals) for freq in freq_sweep for param_vals in values_product]

    results = {}
    errors = []
    start_time = time.time()

    # Prepare a sanitized clone for parallel evaluation.
    sanitized_circuit = circuit.prepare_for_parallel()

    # Batch the sweep points to reduce overhead.
    batch_size = 100  # Tune as needed.
    batches = [sweep_points[i:i+batch_size] for i in range(0, len(sweep_points), batch_size)]

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(evaluate_batch, sanitized_circuit, batch, keys) for batch in batches]
        for future in futures:
            for point in future.result():
                key = (round(point.frequency, 9), tuple(sorted(point.parameters.items())))
                if point.error:
                    errors.append(f"Frequency {point.frequency:.3e} Hz, Params {point.parameters}: {point.error}")
                    results[key] = None  # Alternatively, you could store the point with error details.
                else:
                    results[key] = point.evaluation_result  # Store the full evaluation result.

    elapsed = time.time() - start_time
    stats = {"points": len(sweep_points), "elapsed": elapsed}
    return SweepResult(results, errors, stats)
