import pprint
from io import BytesIO

from pypdf import PdfReader

from internalprocesses import OutlookClient
from .constants import OUTLOOK_CREDENTIALS

outlook = OutlookClient(**OUTLOOK_CREDENTIALS)

query = "D Auto Body Warehouse"

email = outlook.searchMessages(f"?$search=\"\\\"{query}\\\"\"")

attachment = outlook.getEmailAttachments(email["id"])

content = outlook.getEmailAttachmentContent(email["id"], attachment[0]["id"])

lines = PdfReader(BytesIO(content), strict=False).pages[
    0].extract_text().split("\n")

lines = [line.split("  ") for line in lines]

cleaned_lines = []
for line in lines:
    cleaned_line = []
    for data in line:
        if data:
            cleaned_line.append(data.strip())
    cleaned_lines.append(cleaned_line)
    
pprint.pprint(cleaned_lines)
