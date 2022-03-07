from app import orderImportNewThread
from internalAutomation.src.automation import InternalAutomation, orderImport

try:
    automation = InternalAutomation()
    print(automation.unfulfilledOrders)
finally:
    automation.close()
    pass