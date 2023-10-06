import os

FTP_CREDENTIALS = {
    "host": "54.211.94.170",
    "username": "danny",
    "password": os.getenv("FTP-PW"),
    "port": 21
}

FISHBOWL_CREDENTIALS = {
    "username": "danny",
    "password": os.getenv("FISHBOWL-PW"),
    "host": "factorywheelwarehouse.myfishbowl.com",
    "port": 28192
}

OUTLOOK_CREDENTIALS = {
    "data": {
        "tenant_id": "bfe22315-f429-405a-b29e-44f08d06631f",
        "authority": "https://login.microsoftonline.com/bfe22315-f429-405a-b29e-44f08d06631f",
        "username": "danny@factorywheelwarehouse.com",
        "scope": ["Mail.ReadWrite", "Mail.Send"],
        "client_id": "37dee6bf-ece2-45f4-bc23-07cae6d86e73",
        "Tracking": {
            "Coast Invoices": "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_htAAA=",
            "Coast Tracking": "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_ihAAA=",
            "Jante Invoices": "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAQ3_igAAA=",
            "Inbox": "AAMkADJiYmRhODc4LTkzMDEtNGNkZi1hMzYxLTYxZGQwNTI5MGEzOAAuAAAAAAAclAXJVwp9TZpEBy-FAagHAQCUYlSoTaH0RrSZHpqVcQWRAAAAAAEMAAA="
        }
    },
    "password": os.getenv("OUTLOOK-PW"),
    "clientSecret": os.getenv("OUTLOOK-CS")
}

MAGENTO_CREDENTIALS = {
    "accessToken": os.getenv("MAGENTO_AT")
}
