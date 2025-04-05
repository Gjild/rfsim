# frontend/main.py
from frontend.models.state import StateManager
from frontend.controllers.ui_controller import UIController

def main() -> None:
    state = StateManager()
    ui_controller = UIController(state)
    ui_controller.run()

if __name__ == "__main__":
    main()
