from internalprocesses import OutlookClient
from internalprocesses.vendortracking.util import get_tracking_from_outlook
from internalprocesses.vendortracking.constants import TRACKING_PATTERNS
from internalprocesses.vendortracking.trackingchecker import TrackingChecker

if __name__ == "__main__":
    import json
    import os
    from pprint import pprint

    config = json.load(
        open(r"./data/config.json")
    )["APIConfig"]["Outlook"]["Danny"]
    password = os.getenv("OUTLOOK-PW")
    consumerSecret = os.getenv("OUTLOOK-CS")
    outlook = OutlookClient(config, password, consumerSecret)

    tracking = {}
    for po in range(29000, 29010):
        tracking[str(po)] = get_tracking_from_outlook(str(po), outlook)
    tracking["28767"] = get_tracking_from_outlook("28767", outlook)
    pprint(tracking)
