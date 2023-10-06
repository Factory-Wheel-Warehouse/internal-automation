# Outlook API constants
ATTACHMENT_CONTENT_TYPE_KEY = "contentType"
ATTACHMENT_ID_KEY = "id"
EMAIL_ID_KEY = "id"
EMAIL_BODY_KEY = "body"
EMAIL_BODY_CONTENT_KEY = "content"
PDF_CONTENT_TYPE = "application/pdf"

# Carrier constants
UPS = "UPS"
FEDEX = "FedEx"

# Tracking patterns
TRACKING_PATTERNS = {
    FEDEX: r"\d{12}",
    UPS: r"1Z\w{8}\d{8}"
}

# Bing tracking validation
TRACKING_URL = "https://www.bing.com/packagetrackingv2"
TRACKING_NUMBER_KEY = "packnum"
CARRIER_KEY = "carrier"
