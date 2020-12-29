from abc import ABC
from typing import *

from tornado.httpclient import HTTPResponse

from .ilrh import ILogged_RequestHandler

class IResponder(ABC):
    @staticmethod
    def update_error_response(handler: ILogged_RequestHandler, response: HTTPResponse, message: str) -> Optional[HTTPResponse]:
        pass
    @staticmethod
    def get_error_response(handler: ILogged_RequestHandler, code: int, reason: str, message: str) -> HTTPResponse:
        pass
    @staticmethod
    def resp_error(handler: ILogged_RequestHandler, code, reason, message):
        pass
    
    @staticmethod
    def update_success_response(handler: ILogged_RequestHandler, response: HTTPResponse, message: str, result) -> Optional[HTTPResponse]:
        pass
    @staticmethod
    def get_success_response(handler: ILogged_RequestHandler, code: int, reason: str, message: str, result) -> HTTPResponse:
        pass
    @staticmethod
    def resp_success(handler: ILogged_RequestHandler, code: int, reason: str, message: str, result):
        pass

__all__ = \
[
    'IResponder',
]
