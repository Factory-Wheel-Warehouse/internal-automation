import os

DEFAULT_REGION = "us-east-1"

SESSION_PARAMETERS = {
    "region_name": DEFAULT_REGION,
    "aws_access_key_id": os.getenv("AWS-ACCESS-KEY"),
    "aws_secret_access_key": os.getenv("AWS-SECRET-KEY")
}

DYNAMODB_VENDOR_CONFIG_TABLE = "internal_automation_vendor_config"
DYNAMODB_ITEM_KEY = "Items"

SNS_EXCEPTION_TOPIC_ARN = "arn:aws:sns:us-east-1:825222085026:InternalAutomationExceptions"
SNS_EXCEPTION_SUBJECT = "InternalAutomation Encountered an Error"
