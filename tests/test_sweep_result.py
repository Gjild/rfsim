import numpy as np
import pandas as pd
from evaluation.sweep import SweepResult

def test_sweep_result_to_dataframe():
    # Create a dummy SweepResult instance with two points.
    results = {
        (1e9, (("param1", 10), ("param2", 20))): np.array([[1, 2], [3, 4]]),
        (2e9, (("param1", 15), ("param2", 25))): np.array([[5, 6], [7, 8]])
    }
    errors = ["error1", "error2"]
    sweep_result = SweepResult(results, errors, stats={})
    df = sweep_result.to_dataframe()
    # Check that the DataFrame has the expected columns.
    for col in ["frequency", "param1", "param2", "s_matrix"]:
        assert col in df.columns
    # Check that the DataFrame has 2 rows.
    assert len(df) == 2
