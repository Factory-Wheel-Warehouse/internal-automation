from internalAutomation.src.automation import InternalAutomation

try:
    automation = InternalAutomation()
    print(automation.checkLKQQTY("ALY64111U35"))
finally:
    automation.close()