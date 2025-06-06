from src.action.action import Action
from src.action.tracking.upload_action import UploadAction
from src.manager.manager import Manager


class TrackingManager(Manager):

    def get_actions(self) -> list[Action]:
        return [
            UploadAction()
        ]
