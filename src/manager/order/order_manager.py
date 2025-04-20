from src.action.action import Action
from src.action.order.import_action import ImportAction
from src.action.order.notify_action import NotifyAction
from src.manager.manager import Manager


class OrderManager(Manager):

    def get_actions(self) -> list[Action]:
        return [
            ImportAction(),
            NotifyAction()
        ]
