from app import orderImportNewThread
from internalAutomation.src.automation import InternalAutomation, orderImport

try:
    # automation = InternalAutomation()
    # print(automation.unfulfilledOrders)
    orderImport()
finally:
    # automation.close()
    pass