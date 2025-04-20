import logging
import re
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint
from flask import copy_current_request_context
from flask import request

from src.action.action import Action

executor = ThreadPoolExecutor(max_workers=10)


class Manager(ABC):

    def __init__(self):
        self.blueprint = Blueprint(
            self.name,
            __name__,
            url_prefix=f"/ms/{self.name}"
        )
        self._register_actions()
        self._register_sub_managers()

    @property
    def name(self):
        name_ = self.__class__.__name__.replace("Manager", "")
        name_ = re.sub(r'(?<!^)(?=[A-Z])', '-', name_).lower()
        return name_

    def get_actions(self) -> list[Action]:
        return []

    def get_sub_managers(self) -> list["Manager"]:
        return []

    @staticmethod
    def make_handler(action_):
        def handler():
            if action_.async_:
                @copy_current_request_context
                def run_in_context():
                    action_.trigger(request)

                future = executor.submit(run_in_context)
                future.add_done_callback(
                    lambda f: f.exception() and logging.error(
                        f"Exception running {action_.route}",
                        exc_info=f.exception().__traceback__
                    )
                )
                return "Submitted", 202

            try:
                return action_.run(request)
            except Exception as e:
                logging.error(
                    f"Exception {e} thrown during {action_.route}",
                    exc_info=e.__traceback__
                )
                return {"error": str(e)}, 500

        return handler

    def _register_actions(self):
        for i, action in enumerate(self.get_actions()):
            route = getattr(action, "route")
            method = getattr(action, "method")

            self.blueprint.add_url_rule(
                f"/{route}",
                view_func=self.make_handler(action),
                methods=[method],
                endpoint=route
            )

        self.blueprint.add_url_rule("", view_func=lambda: self.list(),
                                    methods=["GET"], )

    def _register_sub_managers(self):
        for sub_manager in self.get_sub_managers():
            self.blueprint.register_blueprint(
                sub_manager.blueprint,
                url_prefix=f"/{sub_manager.name}"
            )

    def list(self):
        outp = {}
        if self.get_actions():
            outp["actions"] = [action.route for action in self.get_actions()]
        if self.get_sub_managers():
            for sm in self.get_sub_managers():
                outp["managers"] = {sm.name: sm.list()}
        if outp:
            return outp
        else:
            return "No endpoints implemented for this process yet"
