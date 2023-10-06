from enum import Enum


class IterableEnum(Enum):

    @classmethod
    def map(cls):
        return iter([(i.name, i.value) for i in cls])
