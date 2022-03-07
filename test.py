from internalAutomation.src.automation import InternalAutomation

try:
    automation = InternalAutomation()
    print(automation.checkRoadReadyQTY("ALY64111U35"))
finally:
    automation.close()