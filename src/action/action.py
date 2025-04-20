import logging
import re
import traceback
from abc import ABC
from abc import abstractmethod
from flask import request

from src.util.aws import post_exception_to_sns


class Action(ABC):

    @property
    def route(self):
        name_ = self.__class__.__name__.replace("Action", "")
        name_ = re.sub(r'(?<!^)(?=[A-Z])', '-', name_).lower()
        return name_

    def trigger(self, request_: request):
        logging.info(f"Executing {self.route} due to request {request_}")
        try:
            res = self.run(request_)
            if not self.async_:
                return res
            else:
                return "Submitted", 202
        except Exception as e:
            logging.error(
                f"Exception {e} thrown during {self.route} execution",
                exc_info=e.__traceback__
            )
            exception = traceback.format_exc()
            message = (f"Exception encountered during "
                       f"{self.__class__.__name__}\n\n\n{exception}")
            post_exception_to_sns(message)

    @property
    def method(self):
        return "GET"

    @property
    def async_(self):
        return True

    def _get_args(self, request_: request):
        return request_.args.to_dict()

    @abstractmethod
    def run(self, request_: request):
        pass
