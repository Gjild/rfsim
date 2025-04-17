# core/io/netlist.py
"""
Load and validate YAML netlists into a CircuitModel.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any

import yaml
from cerberus import Validator

from core.exceptions import RFSimError
from core.parameters.resolver import resolve as resolve_parameters
from core.components.plugin_loader import ComponentFactory
from core.ports.impedance_factory import create_impedance_model_from_config

# Schema for netlist validation
NETLIST_SCHEMA: Dict[str, Any] = {
    "version": {"type": "float", "required": True, "allowed": [2.0]},

    "parameters": {
        "type": "dict", "required": False,
        "valueschema": {"type": ["string", "number"]},
    },

    "external_ports": {
        "type": "list", "required": True, "minlength": 1,
        "schema": {
            "type": "dict", "schema": {
                "name": {"type": "string", "required": True},
                "net":  {"type": "string", "required": True},
                "impedance": {
                    "type": "dict", "required": True,
                    "schema": {
                        "type":     {"type": "string", "required": True, "allowed": ["fixed", "freq_dep", "s1p"]},
                        "value":    {"type": ["string", "number"], "required": False},
                        "function": {"type": "string", "required": False},
                        "file":     {"type": "string", "required": False},
                    },
                },
            },
        },
    },

    "components": {
        "type": "list", "required": True, "minlength": 1,
        "schema": {
            "type": "dict", "schema": {
                "id":     {"type": "string", "required": True},
                "type":   {"type": "string", "required": True},
                "params": {"type": "dict",   "required": False},
                "ports": {
                    "type": "list", "required": True, "minlength": 1,
                    "schema": {"type": "string"},
                },
            },
        },
    },

    "connections": {
        "type": "list", "required": True, "minlength": 1,
        "schema": {
            "type": "dict", "schema": {
                "port": {"type": "string", "required": True, "regex": r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$"},
                "net":  {"type": "string", "required": True},
            },
        },
    },
}


# Data model definitions
@dataclass
class ExternalPortSpec:
    name: str
    net_name: str
    impedance: object  # PortImpedance instance

@dataclass
class ConnectionSpec:
    component_id: str
    port_name: str
    net_name: str

@dataclass
class CircuitModel:
    # Raw parameter expressions
    global_parameters: Dict[str, str] = field(default_factory=dict)
    # External ports mapping name -> spec
    external_ports: Dict[str, ExternalPortSpec] = field(default_factory=dict)
    # Instantiated component objects
    components: List[object] = field(default_factory=list)
    # Connection specs for graph building
    connections: List[ConnectionSpec] = field(default_factory=list)


def _ensure_unique(seq: List[str], kind: str) -> None:
    """Raise *once* if duplicates found in *seq*."""
    dup = {x for x in seq if seq.count(x) > 1}
    if dup:
        raise RFSimError(f"Duplicate {kind}: {', '.join(sorted(dup))}")


def load_netlist(path: Path) -> CircuitModel:
    """Read→validate→instantiate a version‑2.0 netlist."""
    try:
        raw = yaml.safe_load(path.read_text())
    except Exception as exc:
        raise RFSimError(f"Failed to read YAML '{path}': {exc}")

    v = Validator(NETLIST_SCHEMA, allow_unknown=False)
    if not v.validate(raw):
        raise RFSimError(f"Netlist schema violations: {v.errors}")
    doc = v.document

    # ------------------------------------------------------------------
    # Manual integrity / uniqueness checks
    # ------------------------------------------------------------------
    _ensure_unique([ep['name'] for ep in doc['external_ports']], 'external‑port names')
    _ensure_unique([c['id']    for c in doc['components']],    'component IDs')

    # Build CircuitModel skeleton
    model = CircuitModel()

    # ---------- globals ------------------------------------------------
    raw_globals = doc.get('parameters', {}) or {}
    model.global_parameters = {k: str(v) for k, v in raw_globals.items()}

    # ---------- external ports ----------------------------------------
    for ep in doc['external_ports']:
        itype = ep['impedance']['type']
        if itype == 'fixed' and 'value' not in ep['impedance']:
            raise RFSimError(f"External port '{ep['name']}' missing 'value' for fixed impedance")
        if itype == 'freq_dep' and 'function' not in ep['impedance']:
            raise RFSimError(f"External port '{ep['name']}' missing 'function' for freq_dep impedance")
        if itype == 's1p' and 'file' not in ep['impedance']:
            raise RFSimError(f"External port '{ep['name']}' missing 'file' for s1p impedance")
        try:
            imp = create_impedance_model_from_config(ep['impedance'])
        except Exception as exc:
            raise RFSimError(f"Impedance error on external port '{ep['name']}': {exc}")
        model.external_ports[ep['name']] = ExternalPortSpec(ep['name'], ep['net'], imp)

    # ---------- components --------------------------------------------
    for cdoc in doc['components']:
        comp_id = cdoc['id']
        local_exprs = {**model.global_parameters, **(cdoc.get('params') or {})}
        try:
            inst = ComponentFactory.create(cdoc['type'], comp_id, local_exprs)
        except Exception as exc:
            raise RFSimError(f"Cannot instantiate component '{comp_id}': {exc}")
        # port‑order enforcement
        if inst.ports != cdoc['ports']:
            raise RFSimError(
                f"Component '{comp_id}' port order mismatch: netlist {cdoc['ports']} vs impl {inst.ports}"
            )
        model.components.append(inst)

    # ---------- connections -------------------------------------------
    declared_nets = {c['net'] for c in doc['connections']}
    for ep in model.external_ports.values():
        if ep.net_name not in declared_nets:
            raise RFSimError(f"External port '{ep.name}' refers to undeclared net '{ep.net_name}'")

    for conn in doc['connections']:
        comp_id, port_name = conn['port'].split('.', 1)
        comp = next((c for c in model.components if c.id == comp_id), None)
        if comp is None:
            raise RFSimError(f"Connection refers to unknown component '{comp_id}'.")
        if port_name not in comp.ports:
            raise RFSimError(f"Component '{comp_id}' has no port '{port_name}'.")
        model.connections.append(ConnectionSpec(comp_id, port_name, conn['net']))

    return model
