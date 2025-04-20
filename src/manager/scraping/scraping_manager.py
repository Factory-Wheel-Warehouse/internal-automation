from src.action.action import Action
from src.action.scraping.parts_trader_action import PartsTraderAction
from src.manager.manager import Manager


class ScrapingManager(Manager):
    
    def get_actions(self) -> list[Action]:
        return [
            PartsTraderAction()
        ]
