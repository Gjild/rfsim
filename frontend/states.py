# frontend/state.py
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlotTab:
    id: str
    name: str
    type: str  # e.g., "rectangular" or "smith"
    tab_tag: str
    traces: List[str] = field(default_factory=list)
    widget_refs: Dict[str, Any] = field(default_factory=dict)

class StateManager:
    """
    Maintains application state including file paths, simulation status,
    logs, and plot metadata.
    """
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.netlist_path: str = ""
        self.sweep_config_path: str = ""
        self.simulation_running: bool = False
        self.simulation_progress: float = 0.0
        self.simulation_results: Any = None
        self.logs: List[str] = []
        self.plot_tabs: Dict[str, PlotTab] = {}
        self._last_netlist_hash: Optional[str] = None
        self._last_sweep_hash: Optional[str] = None
        self.yaml_editor_text: str = ""
        self.yaml_editor_original: str = ""

    def add_log(self, message: str) -> None:
        """Add a log message with a timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        with self.lock:
            self.logs.append(log_message)
        logger.info(message)

    def needs_simulation(self, hash_file_func) -> bool:
        """Determine if a new simulation is needed based on file changes."""
        netlist_hash = hash_file_func(self.netlist_path)
        sweep_hash = hash_file_func(self.sweep_config_path)
        if (netlist_hash != self._last_netlist_hash) or (sweep_hash != self._last_sweep_hash):
            self._last_netlist_hash = netlist_hash
            self._last_sweep_hash = sweep_hash
            return True
        return False

    # State accessor/mutator functions for plot traces.
    def get_plot_traces(self, plot_id: str) -> List[str]:
        return self.plot_tabs.get(plot_id, PlotTab(plot_id, "", "", "")).traces

    def update_plot_trace(self, plot_id: str, idx: int, new_expr: str) -> None:
        if plot_id in self.plot_tabs:
            self.plot_tabs[plot_id].traces[idx] = new_expr

    def add_plot_trace(self, plot_id: str, expr: str) -> None:
        if plot_id in self.plot_tabs:
            self.plot_tabs[plot_id].traces.append(expr)

    def remove_plot_trace(self, plot_id: str, idx: int) -> None:
        if plot_id in self.plot_tabs:
            del self.plot_tabs[plot_id].traces[idx]
