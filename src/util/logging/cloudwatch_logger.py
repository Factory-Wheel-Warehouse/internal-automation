import sys
from datetime import date

import watchtower

import logging

from src.util.aws import boto3_session
from src.util.constants.aws import DEFAULT_REGION

log_stream_name = f"application.{date.today().isoformat()}.log"
log_group_name = "/ext/heroku/InternalAutomationService"

logger = logging.getLogger()
logger.addHandler(watchtower.CloudWatchLogHandler(
    boto3_client=boto3_session.client("logs", region_name=DEFAULT_REGION),
    log_group_name=log_group_name,
    log_stream_name=log_stream_name
))
logger.addHandler(logging.StreamHandler(sys.stdout))
