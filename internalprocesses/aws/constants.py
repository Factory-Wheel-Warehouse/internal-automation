import os

DEFAULT_REGION = "us-east-1"

SESSION_PARAMETERS = {
    "region_name": DEFAULT_REGION,
    "aws_access_key_id": os.getenv("AWS-ACCESS-KEY"),
    "aws_secret_access_key": os.getenv("AWS-SECRET-KEY")
}
