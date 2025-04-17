# core/io/sweep.py
"""
Load and validate YAML sweep configurations for RFSim v2.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from cerberus import Validator

from core.exceptions import RFSimError


# Cerberus schema for sweep configuration
SWEEP_SCHEMA = {
    'sweep': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'param': {'type': 'string', 'required': True},
                'range': {
                    'type': 'list',
                    'required': False,
                    'schema': {'type': 'float', 'coerce': float},
                    'minlength': 2,
                    'maxlength': 2
                },
                'points': {'type': 'integer', 'required': False, 'coerce': int},
                'scale': {'type': 'string', 'required': False, 'allowed': ['linear', 'log']},
                'values': {'type': 'list', 'required': False},
            }
        }
    }
}


@dataclass
class SweepEntry:
    param: str
    range: Optional[List[float]] = None
    points: Optional[int] = None
    scale: Optional[str] = None
    values: Optional[List[Any]] = None


@dataclass
class SweepConfig:
    sweep: List[SweepEntry]


def load_sweep_config(path: Path) -> SweepConfig:
    """
    Load a YAML sweep configuration file, validate its schema, and return a SweepConfig.

    Raises:
        RFSimError: If file read fails or schema validation fails.
    """
    try:
        raw = yaml.safe_load(path.read_text())
    except Exception as e:
        raise RFSimError(f"Failed to read sweep YAML '{path}': {e}")

    validator = Validator(SWEEP_SCHEMA, allow_unknown=False)
    if not validator.validate(raw):
        raise RFSimError(f"Sweep schema validation errors: {validator.errors}")
    doc: Dict[str, Any] = validator.document

    entries: List[SweepEntry] = []
    for entry in doc['sweep']:
        sweep_entry = SweepEntry(
            param=entry['param'],
            range=entry.get('range'),
            points=entry.get('points'),
            scale=entry.get('scale'),
            values=entry.get('values')
        )
        entries.append(sweep_entry)

    return SweepConfig(sweep=entries)
