from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.services.tracking_update_service import TrackingUpdateService


@dataclass
class UploadAction(Action):
    tracking_service: TrackingUpdateService | None = None

    def __post_init__(self):
        if not self.tracking_service:
            self.tracking_service = TrackingUpdateService()

    def run(self, request_: request):
        self.tracking_service.run()
