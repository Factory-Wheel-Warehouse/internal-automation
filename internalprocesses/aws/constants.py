import os

# Region
DEFAULT_REGION = "us-east-1"

# Credentials
SESSION_PARAMETERS = {
    "region_name": DEFAULT_REGION,
    "aws_access_key_id": os.getenv("AWS-ACCESS-KEY"),
    "aws_secret_access_key": os.getenv("AWS-SECRET-KEY")
}

# SNS
SNS_EXCEPTION_TOPIC_ARN = "arn:aws:sns:us-east-1:825222085026:InternalAutomationExceptions"
SNS_EXCEPTION_SUBJECT = "InternalAutomation Encountered an Error"
