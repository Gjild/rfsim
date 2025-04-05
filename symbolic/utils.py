# symbolic/utils.py
import logging
from typing import Any, Dict

def merge_params(*dicts: Dict[str, Any], conflict_strategy: str = 'override', log_level: int = logging.WARNING) -> Dict[str, Any]:
    """
    Merge multiple parameter dictionaries according to the specified conflict strategy.
    
    Parameters:
        *dicts: Dictionaries to merge.
        conflict_strategy: How to resolve conflicts. Allowed values are:
            - 'override': New values override old ones.
            - 'keep': Keep existing values.
            - 'raise': Raise an exception on conflict.
            - 'combine': Combine values if possible (lists or dicts).
        log_level: The logging level for conflict messages.
    
    Returns:
        A new dictionary with merged parameters.
    
    Raises:
        ValueError: If an unknown conflict strategy is specified.
        Exception: If conflict_strategy is 'raise' and a conflict occurs.
    """
    allowed_strategies = {'override', 'keep', 'raise', 'combine'}
    if conflict_strategy not in allowed_strategies:
        raise ValueError(f"Unknown conflict_strategy '{conflict_strategy}'. Allowed values are: {allowed_strategies}")

    def _merge_value(existing: Any, new: Any) -> Any:
        if existing == new:
            return existing
        if conflict_strategy == 'override':
            logging.log(log_level, f"Parameter conflict: existing value '{existing}' overridden by '{new}'.")
            return new
        elif conflict_strategy == 'keep':
            logging.debug(f"Parameter conflict: keeping existing value '{existing}', ignoring new value '{new}'.")
            return existing
        elif conflict_strategy == 'raise':
            raise Exception(f"Parameter conflict: cannot merge '{existing}' with '{new}'.")
        elif conflict_strategy == 'combine':
            if isinstance(existing, list) and isinstance(new, list):
                combined = existing + new
                logging.log(log_level, f"Parameter conflict: combining lists {existing} and {new} -> {combined}.")
                return combined
            elif isinstance(existing, dict) and isinstance(new, dict):
                return merge_params(existing, new, conflict_strategy='combine', log_level=log_level)
            else:
                logging.log(log_level, f"Parameter conflict: overriding '{existing}' with '{new}'.")
                return new

    result: Dict[str, Any] = {}
    for d in dicts:
        for key, value in d.items():
            if key in result:
                result[key] = _merge_value(result[key], value)
            else:
                result[key] = value
    return result
