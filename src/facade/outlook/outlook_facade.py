import logging
import os

import requests
import msal
from datetime import date


# TODO: Refactor with `from msgraph import GraphServiceClient`
# link: https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph
# -rest-1.0&tabs=python

class OutlookFacade:
    """
    Class for connecting to the outlook API.

    Attributes
    ----------

    data: dict
        config data
    
    Methods
    -------

    """

    DATA = {
        "tenant_id": "bfe22315-f429-405a-b29e-44f08d06631f",
        "authority": "https://login.microsoftonline.com/bfe22315-f429-405a"
                     "-b29e-44f08d06631f",
        "username": "danny@factorywheelwarehouse.com",
        "scope": ["Mail.ReadWrite", "Mail.Send"],
        "client_id": "37dee6bf-ece2-45f4-bc23-07cae6d86e73",
        "Tracking": {
            "Coast Invoices":
                "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_htAAA=",
            "Coast Tracking":
                "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_ihAAA=",
            "Jante Invoices":
                "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_igAAA=",
            "Inbox":
                "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAAAAEMAAA="
        }
    }
    PASSWORD = os.getenv("OUTLOOK-PW")
    CLIENT_SECRET = os.getenv("OUTLOOK-CS")

    def __init__(self):
        self.endpoint = "https://graph.microsoft.com/v1.0/me/"

    def requestPermsission(self):
        url = 'https://login.microsoftonline.com/bfe22315-f429-405a-b29e' \
              '-44f08d06631f/oauth2/v2.0/authorize?client_id=37dee6bf-ece2' \
              '-45f4-bc23-07cae6d86e73&response_type=code&response_mode' \
              '=query&scope=mail.send%20mail.readwrite&state=12345'

    def getClientApp(self):
        app = msal.ConfidentialClientApplication(
            self.DATA["client_id"], client_credential=self.CLIENT_SECRET,
            authority=self.DATA["authority"]
        )
        return app

    def getAccessToken(self, app, data):
        token = None
        accounts = app.get_accounts(username=data["username"])
        if accounts:
            token = app.acquire_token_silent(
                data["scope"], account=accounts[0]
            )
        if not token:
            token = app.acquire_token_by_username_password(
                username=data["username"],
                password=self.PASSWORD,
                scopes=data["scope"]
            )
        if 'access_token' in token:
            return token['access_token']
        else:
            description = token.get("error_description")
            if not description:
                description = "No error description provided"
            raise Exception(f"Outlook authentication error.\n{description}")

    def login(self):
        app = self.getClientApp()
        self.accessToken = self.getAccessToken(app, self.DATA)
        if self.accessToken:
            self.headers = {'Authorization': f'Bearer {self.accessToken}'}

    def get_email_attachments(self, emailID: str) -> list | None:
        email = requests.get(
            self.endpoint + "/messages/" + emailID + "/attachments",
            headers=self.headers
        ).json()
        attachments = email.get("value")
        if not attachments:
            return []
        return attachments

    def getEmailAttachmentContent(self, emailId, attachmentId):
        return requests.get(
            self.endpoint + "/messages/" + emailId + \
            "/attachments/" + attachmentId + "/$value",
            headers=self.headers
        ).content

    def getSourceListEmailID(self):
        subject = 'FW: Source File '
        dateList = str(date.today()).split("-")
        subject += f"{dateList[2]}-{dateList[1]}-{dateList[0]}"
        date_ = dateList[1] + "/" + dateList[2] + "/" + dateList[0]
        searchFilter = f'?$search="hasAttachment:true AND subject:{subject}'
        searchFilter += f' AND received:{date_}"'
        inbox = self.DATA["Tracking"]["Inbox"]
        messages = requests.get(
            self.endpoint + "/mailFolders/" + inbox + "/messages" +
            searchFilter,
            headers=self.headers
        ).json()
        return messages["value"][0]["id"]

    def getSourceList(self):
        return self.getEmailAttachment(self.getSourceListEmailID())

    def getUnreadEmails(self, mailFolder):
        searchFilter = '?$search="isRead:false"'
        requestEndpoint = self.endpoint + "mailFolders/" + \
                          self.DATA["Tracking"][
                              mailFolder] + "/messages" + searchFilter
        folder = requests.get(
            requestEndpoint,
            headers=self.headers
        ).json()
        unreadMessages = [message for message in folder["value"]]
        while "@odata.nextLink" in folder:
            folder = requests.get(
                folder["@odata.nextLink"],
                headers=self.headers
            ).json()
            unreadMessages += [message for message in folder["value"]]
        return unreadMessages

    def searchMessages(self, searchQuery, getAll=False):
        endpoint = self.endpoint + "messages/" + searchQuery
        response = requests.get(
            endpoint,
            headers=self.headers
        ).json()["value"]
        if len(response) > 0 and not getAll:
            return response[0]
        return response

    def markRead(self, messageID):
        self.headers['Content-type'] = 'application/json'
        requests.patch(
            self.DATA["coastTracking"] + "/" + messageID,
            json={"isRead": True},
            headers=self.headers
        )
        del self.headers['Content-type']

    def addCCRecipients(self, jsonData, cc):
        if isinstance(cc, list):
            for recipient in cc:
                formattedRecipient = {
                    "emailAddress": {
                        "address": recipient
                    }
                }
                jsonData["message"]["ccRecipients"].append(formattedRecipient)
        elif isinstance(cc, str):
            formattedRecipient = {
                "emailAddress": {
                    "address": cc
                }
            }
            jsonData["message"]["ccRecipients"].append(formattedRecipient)

    def sendMail(
            self, to, subject, body, cc=None, attachment=None,
            attachmentName=None, contentType="text"
    ):
        url = 'https://graph.microsoft.com/v1.0/me/sendMail'
        headers = self.headers
        jsonData = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": contentType,
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to
                        }
                    }
                ],
                "ccRecipients": [],
                "attachments": []
            },
            "saveToSentItems": True
        }
        if cc:
            self.addCCRecipients(jsonData, cc)
        if attachment:
            jsonData["message"]["attachments"].append(
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachmentName,
                    "contentBytes": attachment
                }
            )
        resp = requests.post(url=url, json=jsonData, headers=headers)
        return resp
