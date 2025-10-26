from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.services.inventory_sync_service import InventorySyncService


@dataclass
class DynamoAction(Action):
    inventory_service: InventorySyncService | None = None

    def __post_init__(self):
        if not self.inventory_service:
            self.inventory_service = InventorySyncService()

    def run(self, request_: request):
        self.inventory_service.sync_dynamo()
