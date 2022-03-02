import requests
import msal
from datetime import date

class OutlookConnection():

    """
    Class for connecting to the outlook API.

    Attributes
    ----------

    data : dict
        config data
    
    Methods
    -------

    """

    def __init__(self, data, password, clientSecret):
        print("Initializing Outlook connection.")
        self.password = password
        self.clientSecret = clientSecret
        self.data = data
        self.endpoint = "https://graph.microsoft.com/v1.0/me/"
        self.login()

    def requestPermsission(self):
        url = 'https://login.microsoftonline.com/bfe22315-f429-405a-b29e-44f08d06631f/oauth2/v2.0/authorize?client_id=37dee6bf-ece2-45f4-bc23-07cae6d86e73&response_type=code&response_mode=query&scope=mail.send%20mail.readwrite&state=12345'

    def getClientApp(self):
        app = msal.ConfidentialClientApplication(
            self.data["client_id"], client_credential=self.clientSecret,
            authority=self.data["authority"]
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
                data["username"], 
                self.password,
                scopes=data["scope"]
            )
        if 'access_token' in token:
            return token['access_token']
        else:
            return None

    def login(self):
        app = self.getClientApp()
        self.accessToken = self.getAccessToken(app, self.data)
        if self.accessToken:
            self.headers = {'Authorization': f'Bearer {self.accessToken}'}
        print("Outlook connection successful.")

    def getEmailAttachment(self, emailID):
        attachments = requests.get(
                self.endpoint + "/messages/" + emailID + "/attachments",
                headers=self.headers
            ).json()
        attachmentID = attachments["value"][0]["id"]
        attachment = requests.get(
                self.endpoint + "/messages/" + emailID + \
                    "/attachments/" + attachmentID + "/$value",
                headers=self.headers
            )
        return attachment
    
    def getSourceListEmailID(self):
        subject = 'FW: Source File '
        dateList = str(date.today()).split("-")
        subject += f"{dateList[2]}-{dateList[1]}-{dateList[0]}"
        date_ = dateList[1] + "/" + dateList[2] + "/" + dateList[0]
        searchFilter = f'?$search="hasAttachment:true AND subject:{subject}'
        searchFilter += f' AND received:{date_}"'
        inbox = self.data["Tracking"]["Inbox"]
        messages = requests.get(
                self.endpoint + "/mailFolders/" + inbox + "/messages" + searchFilter,
                headers=self.headers
            ).json() 
        return messages["value"][0]["id"]
    
    def getSourceList(self):
        return self.getEmailAttachment(self.getSourceListEmailID())

    def getUnreadEmails(self, mailFolder):
        searchFilter = '?$search="isRead:false"'
        requestEndpoint = self.endpoint + "mailFolders/" + \
            self.data["Tracking"][mailFolder] + "/messages" + searchFilter
        folder = requests.get(
            requestEndpoint,
            headers = self.headers
        ).json()
        unreadMessages = [message for message in folder["value"]]
        while "@odata.nextLink" in folder:
            folder = requests.get(
                folder["@odata.nextLink"],
                headers = self.headers
            ).json()
            unreadMessages += [message for message in folder["value"]]
        return unreadMessages

    def searchMessages(self, searchQuery):
        endpoint = self.endpoint + "messages/" + searchQuery
        response = requests.get(
            endpoint,
            headers = self.headers
        ).json()["value"]
        if len(response) > 0:
            return response[0]

    def markRead(self, messageID):
        self.headers['Content-type'] = 'application/json'
        requests.patch(
            self.data["coastTracking"] + "/" + messageID,
            json={"isRead": True},
            headers=self.headers
        )
        del self.headers['Content-type']

    def addCCRecipients(self, jsonData, cc):
        if isinstance(cc, list):
            for recipient in cc:
                formattedRecipient = {
                    "emailAddress" : {
                        "address" : recipient
                    }
                }
                jsonData["message"]["toRecipients"].append(formattedRecipient)
        elif isinstance(cc, str):
            formattedRecipient = {
                "emailAddress" : {
                    "address" : cc
                }
            }
            jsonData["message"]["toRecipients"].append(formattedRecipient)
            
    def sendMail(self, to, subject, body, cc = None):
        url = 'https://graph.microsoft.com/v1.0/me/sendMail'
        headers = self.headers
        jsonData = {
            "message" : {
                "subject" : subject,
                "body" : {
                    "contentType" : "text",
                    "content" : body
                },
                "toRecipients" : [
                    {
                        "emailAddress" : {
                            "address" : to
                        }
                    }
                ],
            },
            "saveToSentItems" : True
        }
        if cc:
            self.addCCRecipients(jsonData, cc)
        resp = requests.post(url=url, json=jsonData, headers=headers)
        return resp

# def run():
#     app, jsonData = getClientApp()
#     accessToken = getAccessToken(app, jsonData)
#     if accessToken != None:
#         headers = {'Authorization': 'Bearer {}'.format(accessToken)}
#         unreadInvoices = getUnreadInvoices(accessToken, headers, jsonData)
#         trackingInfo = getTrackingInfo(unreadInvoices, jsonData, headers)
#         pprint(trackingInfo)
#         print(len(trackingInfo))

# if __name__ == "__main__":
#     run()
# 
# outlook = OutlookConnection()
# pprint(outlook.getUnreadInvoices())


"""
Connect to eBay api to pull orders with no tracking info

Add to watch list

Check invoice POs in fishbowl DB to see if eBay order. If not eBay order
do NOT mark as read and leave it alone.

https://login.microsoftonline.com/bfe22315-f429-405a-b29e-44f08d06631f/oauth2/v2.0/authorize?client_id=37dee6bf-ece2-45f4-bc23-07cae6d86e73&response_type=code&response_mode=query&scope=mail.send%20mail.readwrite&state=12345

"""