from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.dao import InventoryDAO
from src.domain.inventory.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade


@dataclass
class DynamoAction(Action):
    ftp: FTPFacade = None
    fishbowl_facade: FishbowlFacade = None
    inventory: Inventory = Inventory()
    inventory_dao: InventoryDAO = InventoryDAO()

    def run(self, request_: request):
        self.fishbowl_facade.start()
        self.ftp.start()
        self.inventory.build(self.ftp, self.fishbowl_facade)
        self.fishbowl_facade.close()
        self.ftp.close()
        self.inventory_dao.delete_all_items()
        self.inventory_dao.batch_write_items(
            self.inventory.convert_to_entries()
        )
