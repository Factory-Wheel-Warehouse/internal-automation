from io import BytesIO
from pypdf import PdfReader
import json
import os
import re
import requests
from pprint import pprint
from internalprocesses.outlookapi.outlook import OutlookConnection

TRACKING_PATTERNS = {
    "FedEx": r"\d{12}",
    "UPS": r"1Z[a-z|A-Z|0-9]{8}[0-9]{8}"
}

config = json.load(open(r"./data/config.json"))["APIConfig"]["Outlook"]["Danny"]
password = os.getenv("OUTLOOK-PW")
consumerSecret = os.getenv("OUTLOOK-CS")
outlook = OutlookConnection(config, password, consumerSecret)

def trackingNumberSearch(poNum, outlook: OutlookConnection):
    emails = outlook.searchMessages(f"?$search=\"\\\"{poNum}\\\"\"", getAll=True)
    return emails

def searchEmailPDFs(outlook, pattern, emailId):
    candidates = []
    for attachment in outlook.getEmailAttachments(emailId):
        type_, id_ = attachment["contentType"], attachment["id"]
        if type_ == "application/pdf":
            attachmentContent = outlook.getEmailAttachmentContent(
                emailId, id_
            )
            reader = PdfReader(BytesIO(attachmentContent), strict=False)
            for page in range(len(reader.pages)):
                text = reader.pages[page].extract_text(0)
                candidates += re.findall(pattern, text)
    return candidates

def getTrackingCandidates(poNum: str, 
    outlook: OutlookConnection,
    pattern: str,
) -> set:
    candidates = []
    emails = trackingNumberSearch(poNum, outlook)
    for email in emails:
        id_, body = email["id"], email["body"]["content"]
        candidates += re.findall(pattern, body)
        if not candidates:
            candidates += searchEmailPDFs(outlook, pattern, id_)
    return set(candidates)

def getValidTrackings(trackingCandidates: set[str], carrier: str) -> list[str]:
    validTrackings = []
    for candidate in trackingCandidates:
        if carrier == "UPS":
            validTrackings.append(candidate)
        elif carrier == "FedEx" and fedexTrackingIsValid(candidate):
            validTrackings.append(candidate)
    return validTrackings

def fedexTrackingIsValid(trackingNumber: str) -> bool:
    url = f"https://www.bing.com/packagetrackingv2"
    params = {'packNum': trackingNumber, "carrier": "FedEx"}
    response = requests.get(url, params=params)
    return len(response.text) > 0

def getTracking(poNum, outlook):
    valid = {}
    for carrier, pattern in TRACKING_PATTERNS.items():
        trackingCandidates = getTrackingCandidates(poNum, outlook, pattern)
        validTrackings = getValidTrackings(trackingCandidates, carrier)
        if validTrackings:
            valid[carrier] = validTrackings
    return valid
    

tracking = {}
for po in range(29000, 29010):
    tracking[str(po)] = getTracking(str(po), outlook)
tracking["28767"] = getTracking("28767", outlook)
pprint(tracking)
