class Port:
    def __init__(self, name, index, connected_node=None, Z0=50):
        self.name = name
        self.index = index
        self.connected_node = connected_node  # instance of Node
        self.Z0 = Z0
        
    def __repr__(self):
        cn = self.connected_node.name if self.connected_node else None
        return f"<Port {self.name} (index={self.index}, node={cn})>"
