from internalAutomation.src.automation import InternalAutomation

try:
    automation = InternalAutomation()
finally:
    automation.close()