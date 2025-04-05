# frontend/utils/tags.py
from uuid import uuid4

class TagRegistry:
    """
    Centralized management of widget tag strings.
    """
    YAML_EDITOR = "yaml_editor"
    LOG_TEXT = "log_text_tag"
    PROGRESS_BAR = "progress_bar_tag"
    # … (other standard tags)

    @staticmethod
    def generate_tag(prefix: str, plot_id: str, identifier: str = None) -> str:
        """
        Generate a unique tag based on a prefix, plot ID, and an optional identifier.
        Uses UUIDs to avoid collisions if identifier is not provided.
        """
        if identifier:
            return f"{prefix}_{plot_id}_{hash(identifier)}"
        return f"{prefix}_{plot_id}_{uuid4().hex[:8]}"
