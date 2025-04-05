# frontend/utils/tag_factory.py
import uuid

class TagFactory:
    @staticmethod
    def generate_tag(prefix: str, plot_id: str, identifier: str = None) -> str:
        """
        Generate a unique tag based on a prefix, plot ID, and an optional identifier.
        """
        if identifier:
            return f"{prefix}_{plot_id}_{hash(identifier)}"
        return f"{prefix}_{plot_id}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def get_trace_input_tag(plot_id: str, idx: int) -> str:
        return f"trace_input_{plot_id}_{idx}"

    @staticmethod
    def get_plot_container_tag(plot_id: str) -> str:
        return f"plot_container_{plot_id}"
