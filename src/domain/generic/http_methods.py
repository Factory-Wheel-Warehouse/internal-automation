from enum import Enum


class HTTPMethods(str, Enum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
