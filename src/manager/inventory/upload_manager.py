from src.action.action import Action
from src.action.inventory.upload.dynamo_action import DynamoAction
from src.action.inventory.upload.ftp_action import FtpAction
from src.action.inventory.upload.pricing_action import PricingAction
from src.manager.manager import Manager


class UploadManager(Manager):

    def get_actions(self) -> list[Action]:
        return [
            FtpAction(),
            DynamoAction(),
            PricingAction()
        ]
