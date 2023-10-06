from src.manager.manager import Manager


class TestManager(Manager):

    @property
    def endpoint(self):
        return "manager"

    @Manager.action
    def action_1(self):
        return "action-1"

    @Manager.action
    def action_2(self):
        return "action-2"

    @Manager.sub_manager
    def sub_manager(self):
        return TestSubManager()


class TestSubManager(Manager):

    @property
    def endpoint(self):
        return "sub_manager"

    @Manager.action
    def sub_action_1(self):
        return "sub_action_1"

    @Manager.action
    def sub_action_2(self):
        return "sub_action_2"
