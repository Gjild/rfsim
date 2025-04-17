# core/components/plugin_loader.py
"""
Plugin loader for RFSim v2 components.
Discovers built-in core.components modules and third-party plugins via entry points.
Supports dynamic registration for manual plugins.
"""
from typing import Dict, Type, Any

try:
    # Python 3.10+ entry points API
    from importlib.metadata import entry_points, EntryPoint
except ImportError:
    from importlib_metadata import entry_points, EntryPoint  # type: ignore

from core.exceptions import RFSimError
from core.components.base import Component


class ComponentFactory:
    """
    Factory for creating component instances by type name.
    Auto-registers built-in core.components modules and discovers third-party plugins.
    """
    _registry: Dict[str, Type[Component]] = {}
    _loaded: bool = False

    @classmethod
    def load_plugins(cls) -> None:
        """
        Discover and load built-in modules under core.components (to register their classes),
        then discover entry point plugins under 'rfsim.components' group.
        """
        if cls._loaded:
            return
        cls._loaded = True

        # 1) Auto-import all modules in core.components to register built-ins
        import pkgutil, importlib
        import core.components as _builtin_pkg
        for _, module_name, _ in pkgutil.iter_modules(_builtin_pkg.__path__):
            try:
                importlib.import_module(f"core.components.{module_name}")
            except Exception:
                # Ignore import errors for other modules
                continue

        # 2) Discover third-party plugins via entry points
        eps = entry_points()
        comp_eps = []
        if hasattr(eps, 'get'):
            comp_eps = eps.get('rfsim.components', [])
        else:
            comp_eps = [ep for ep in eps if getattr(ep, 'group', None) == 'rfsim.components']

        for ep in comp_eps:  # type: EntryPoint
            try:
                comp_cls = ep.load()
            except Exception:
                continue
            if not issubclass(comp_cls, Component):
                continue
            type_name = getattr(comp_cls, 'type_name', None)
            if not isinstance(type_name, str):
                continue
            cls._registry[type_name.lower()] = comp_cls

    @classmethod
    def register(cls, comp_cls: Type[Component]) -> None:
        """
        Manually register a component class.
        The class must define a unique `type_name` attribute.
        """
        if not issubclass(comp_cls, Component):
            raise RFSimError(f"Cannot register non-Component class: {comp_cls}")
        type_name = getattr(comp_cls, 'type_name', None)
        if not isinstance(type_name, str):
            raise RFSimError(f"Component class {comp_cls} lacks a valid `type_name` attribute.")
        cls._registry[type_name.lower()] = comp_cls

    @classmethod
    def create(cls, type_name: str, comp_id: str, params: Dict[str, Any]) -> Component:
        """
        Instantiate a component by its type name (case-insensitive).
        Raises RFSimError for unknown types or instantiation errors.
        """
        cls.load_plugins()
        key = type_name.lower()
        comp_cls = cls._registry.get(key)
        if comp_cls is None:
            raise RFSimError(f"Unknown component type: '{type_name}'")
        try:
            return comp_cls(comp_id, params)
        except Exception as e:
            raise RFSimError(f"Error instantiating component '{comp_id}' of type '{type_name}': {e}")
