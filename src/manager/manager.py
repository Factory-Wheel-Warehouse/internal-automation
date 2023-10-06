from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from threading import Thread

from src.util.logging import log_exceptions


@dataclass
class Manager(ABC):

    @property
    @abstractmethod
    def endpoint(self):
        return NotImplementedError

    def list(self):
        actions = [f"/{action}/" for action in self.get_actions()]
        sub_managers = [f"/{sm.endpoint}/" for sm in self.get_sub_managers()]
        outp = ""
        if actions:
            outp += f"Process manager actions are {actions}"
        if sub_managers:
            outp += f"Process manager actions are {sub_managers}"
        if outp:
            return outp
        else:
            "No endpoints implemented for this process yet"

    @staticmethod
    def action(func: callable):
        func.is_action = True
        return func

    @staticmethod
    def sub_manager(func: callable):
        func.is_sub_manager = True
        return func

    @staticmethod
    def asynchronous(response: str = "Action successfully triggered!"):
        def decorator(fn: callable):
            def run(*args, **kwargs):
                t = Thread(target=fn, args=args, kwargs=kwargs)
                t.start()
                return response

            run.__name__ = fn.__name__
            return run

        return decorator

    def _wrap_actions(self):
        attrs = [[name, getattr(type(self), name, None)] for name in dir(self)]
        for attr_name, attr in attrs:
            if hasattr(attr, "__call__"):
                if getattr(attr, "is_action", False):
                    setattr(self,
                            attr_name,
                            log_exceptions(getattr(self, attr_name)))

    def get_actions(self):
        attrs = [[name, getattr(type(self), name, None)] for name in dir(self)]
        actions = []
        for attr_name, attr in attrs:
            if hasattr(attr, "__call__"):
                if getattr(attr, "is_action", False):
                    actions.append(attr_name)
        return actions

    def get_sub_managers(self):
        attrs = [[name, getattr(type(self), name, None)] for name in dir(self)]
        sub_managers = []
        for attr_name, attr in attrs:
            if hasattr(attr, "__call__"):
                if getattr(attr, "is_sub_manager", False):
                    sub_managers.append(attr(self))
        return sub_managers
