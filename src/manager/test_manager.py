from src.manager.manager import Manager


class TestManager(Manager):
    def __init__(self, fishbowl_facade=None):
        super().__init__(fishbowl_facade)

    @Manager.action
    def action_1(self):
        return "ACTION 1"

    @Manager.action
    def action_2(self):
        return "ACTION_2"
