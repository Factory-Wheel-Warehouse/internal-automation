from enum import Enum


class HTTPMethods(Enum(str)):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
