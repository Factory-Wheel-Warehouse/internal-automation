import sys
from datetime import date

import watchtower

import logging

log_stream_name = f"application.{date.today().isoformat()}.log"
log_group_name = "/ext/heroku/InternalAutomationService"

logger = logging.getLogger()
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group_name=log_group_name,
    log_stream_name=log_stream_name
))
logger.addHandler(logging.StreamHandler(sys.stdout))
