class Node:
    def __init__(self, name, is_ground=False, label="", net_class="signal"):
        self.name = name
        self.is_ground = is_ground
        self.label = label
        self.net_class = net_class
