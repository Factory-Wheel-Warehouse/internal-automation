import asyncio
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from threading import Thread

from src.facade.fishbowl import FishbowlFacade


@dataclass
class Manager(ABC):

    @property
    @abstractmethod
    def endpoint(self):
        return NotImplementedError

    def __init__(self):
        pass

    def list(self):
        actions = [f"/{action}/" for action in self.get_actions()]
        endpoints = ""
        if len(actions) >= 3:
            endpoints = f"{', '.join(actions[:-1])}, and {actions[-1]}"
        elif len(actions) == 2:
            endpoints = " and ".join(actions)
        elif len(actions) == 1:
            endpoints = actions[0]
        if endpoints:
            return f"Process manager endpoints are {endpoints}"
        return "No endpoints implemented for this process yet"

    @staticmethod
    def action(func: callable):
        func.is_action = True
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

    def get_actions(self):
        attrs = [[name, getattr(type(self), name, None)] for name in dir(self)]
        actions = []
        for attr_name, attr in attrs:
            if hasattr(attr, "__call__") and getattr(attr, "is_action", False):
                actions.append(attr_name)
        return actions
