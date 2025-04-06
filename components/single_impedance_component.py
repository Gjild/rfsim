import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.utils import merge_params
from symbolic.evaluator import resolve_all_parameters
    

class SingleImpedanceComponent(TwoPortComponent):
    """
    For resistor, inductor, capacitor. Now we produce the Y stamp (not Z).
    """
    type_name: str = "undefined"
    default_params: dict = {}
    param_key: str = "X"  # e.g. R, C, L

    _ymatrix_builder = None  # Instead of _zmatrix_builder

    def __init__(self, id: str, params: dict = None) -> None:
        super().__init__(id, [], params)
        # Re-initialize your two ports
        from core.topology.port import Port
        self.ports = [Port("1", 0, None), Port("2", 1, None)]
        # Merge default and user-provided:
        all_params = merge_params(self.default_params, params or {})
        self.params = all_params
        # We delay picking the series or shunt mixin until stamping time

    def impedance_expr(self, freq: float, value: float) -> complex:
        raise NotImplementedError

    def pick_ymatrix_mixin(self):
        from components.two_port_mixin import SeriesTwoPortYMNAStamp, ShuntTwoPortYMNAStamp
        """
        Decide if we are 'series' or 'shunt' based on whether port2 is ground.
        """
        port2_node = self.ports[1].connected_node
        if port2_node is not None and getattr(port2_node, 'is_ground', False):
            return ShuntTwoPortYMNAStamp()
        else:
            return SeriesTwoPortYMNAStamp()

    def get_ymatrix(self, freq: float, params: dict) -> np.ndarray:
        """
        Return the 2x2 Y stamp for this device at the given frequency/params.
        """
        merged = merge_params(self.params, params or {})
        resolved = resolve_all_parameters(merged)
        value = resolved[self.param_key]
        Z = self.impedance_expr(freq, value)
        if abs(Z) < 1e-30:
            # handle zero or nearly zero impedance (short) → infinite Y
            Y_dev = 1e12  # or something large
        else:
            Y_dev = 1.0 / Z

        # Lazy pick of series vs shunt.
        if self._ymatrix_builder is None:
            self._ymatrix_builder = self.pick_ymatrix_mixin()

        return self._ymatrix_builder.build_two_port_admittance(Y_dev)
    
    # Keep get_smatrix() inherited from TwoPortComponent, but we must override
    # get_zmatrix as well, if it’s called. We can define it in a simple way:
    def get_zmatrix(self, freq, params):
        """
        If some user calls get_zmatrix, we can do: Z = inverse of get_ymatrix
        (but that is not how the MNA approach is typically used).
        We'll define it for completeness:
        """
        Y = self.get_ymatrix(freq, params)
        from utils.matrix import robust_inv
        Y_inv = robust_inv(Y, reg=1e-12)
        return Y_inv
