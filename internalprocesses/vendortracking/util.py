import re
from io import BytesIO

import requests
from pypdf import PdfReader

from internalprocesses import FBConnection
from internalprocesses.outlookapi.outlook import OutlookClient
from internalprocesses.vendortracking.constants import *


def po_num_email_search(po_num: str, outlook: OutlookClient) -> list:
    """
    Searches the account connected in the Outlook connection for emails
    containing the exact PO number

    :param po_num: purchase order number to search for
    :param outlook: connected outlook account
    :return:
    """
    search_query = f"?$search=\"\\\"{po_num}\\\"\""
    emails = outlook.searchMessages(search_query, getAll=True)
    return emails


def get_pdf_attachments(email_id: str,
                        outlook: OutlookClient) -> list[bytes]:
    """
    Retrieves pdf attachments on the specified email using the outlook client

    :param email_id: email id to retrieve attachments from
    :param outlook: Outlook account to use
    :return: list of pdf attachments as bytes
    """
    attachments_as_bytes = []
    for attachment in outlook.getEmailAttachments(email_id):
        type_ = attachment[ATTACHMENT_CONTENT_TYPE_KEY]
        id_ = attachment[ATTACHMENT_ID_KEY]
        if type_ == PDF_CONTENT_TYPE:
            attachments_as_bytes.append(outlook.getEmailAttachmentContent(
                email_id, id_
            ))
    return attachments_as_bytes


def search_email_pdfs(attachments: list,
                      pattern: str) -> list[str]:
    """
    Parses pdf attachments of specified email searching for tracking number
    candidates

    :param attachments: email attachments to search
    :param pattern: tracking number pattern to search for
    :return: tracking number candidates
    """
    candidates = []
    for attachment in attachments:
        reader = PdfReader(BytesIO(attachment), strict=False)
        for page in range(len(reader.pages)):
            text = reader.pages[page].extract_text(0)
            candidates += re.findall(pattern, text)
    return candidates


def get_tracking_candidates(emails: list,
                            outlook: OutlookClient,
                            pattern: str,
                            ) -> set[str]:
    """
    Searches emails for tracking number candidates matching the pattern. If
    no candidates are found in the email body, pdf attachments are searched
    if applicable.

    :param emails: the retrieved email matches
    :param outlook: connected O account
    :param pattern: tracking number pattern
    :return: set of tracking number candidates
    """
    candidates = []
    for email in emails:
        id_ = email[EMAIL_ID_KEY]
        body = email[EMAIL_BODY_KEY][EMAIL_BODY_CONTENT_KEY]
        candidates += re.findall(pattern, body)
        if not candidates:
            pdf_attachments = get_pdf_attachments(id_, outlook)
            candidates += search_email_pdfs(pdf_attachments, pattern)
    return set(candidates)


def get_valid_tracking_numbers(tracking_candidates: set[str],
                               carrier: str) -> list[str]:
    """
    Checks each tracking candidate number for validity. UPS numbers are not
    checked via Bing due to their uniqueness.
    See TRACKING_URL in constants.py

    :param tracking_candidates: potential tracking numbers
    :param carrier: proposed tracking number carrier
    :return: list of valid tracking numbers
    """
    valid_tracking_numbers = []
    if carrier == UPS:
        return list(tracking_candidates)
    for candidate in tracking_candidates:
        if tracking_is_valid(candidate, carrier):
            valid_tracking_numbers.append(candidate)
    return valid_tracking_numbers


def tracking_is_valid(tracking_number: str, carrier: str) -> bool:
    url = TRACKING_URL
    params = {
        TRACKING_NUMBER_KEY: tracking_number,
        CARRIER_KEY: carrier
    }
    response = requests.get(url, params=params)
    return len(response.text) > 0


def get_tracking_from_outlook(po_num: str, outlook: OutlookClient):
    valid = {}
    emails = po_num_email_search(po_num, outlook)
    for carrier, pattern in TRACKING_PATTERNS.items():
        candidates = get_tracking_candidates(emails, outlook, pattern)
        valid_numbers = get_valid_tracking_numbers(candidates, carrier)
        if valid_numbers:
            valid[carrier] = valid_numbers
    return valid
