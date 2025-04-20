from src.action.action import Action
from src.action.inventory.email_inventory_action import EmailInventoryAction
from src.manager.inventory.upload_manager import UploadManager
from src.manager.manager import Manager


class InventoryManager(Manager):

    def get_sub_managers(self) -> list[Manager]:
        return [
            UploadManager()
        ]

    def get_actions(self) -> list[Action]:
        return [
            EmailInventoryAction()
        ]
