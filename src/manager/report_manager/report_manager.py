from src.action.action import Action
from src.action.report.quatity_sold_action import QuantitySoldAction
from src.manager.manager import Manager


class ReportManager(Manager):
    def get_actions(self) -> list[Action]:
        return [
            QuantitySoldAction()
        ]
