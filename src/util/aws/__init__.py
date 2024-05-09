import boto3

from src.util.constants.aws import DEFAULT_REGION
from src.util.constants.aws import SESSION_PARAMETERS
from src.util.constants.aws import SNS_EXCEPTION_SUBJECT
from src.util.constants.aws import SNS_EXCEPTION_TOPIC_ARN

boto3_session = boto3.Session(**SESSION_PARAMETERS)


def post_exception_to_sns(exception_message):
    sns = boto3_session.client("sns", DEFAULT_REGION)
    sns.publish(TopicArn=SNS_EXCEPTION_TOPIC_ARN,
                Message=exception_message,
                Subject=SNS_EXCEPTION_SUBJECT)
