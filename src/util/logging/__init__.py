import logging
import sys
from datetime import date

import watchtower

from src.util.aws import boto3_session
from src.util.constants.aws import DEFAULT_REGION
from src.util.logging.JsonLogFormatter import JsonLogFormatter
from src.util.logging.sns_exception_logging_decorator import log_exceptions


def _setup_json_handler(handler):
    handler.setFormatter(JsonLogFormatter())
    return handler


def set_up_logging():
    # Set up logging
    logging.basicConfig(**{
        "handlers": [
            _setup_json_handler(
                watchtower.CloudWatchLogHandler(
                    boto3_client=boto3_session.client(
                        "logs",
                        region_name=DEFAULT_REGION
                    ),
                    log_group_name="/ext/heroku/InternalAutomationService",
                    log_stream_name=f"application."
                                    f"{date.today().isoformat()}.log"
                )
            ),
            _setup_json_handler(
                logging.StreamHandler(sys.stdout)
            )
        ],
        "level": "INFO"
    })

    # Test log
    logging.info("Logging with JSON formatting and watchtower is active.")
