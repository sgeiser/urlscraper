from abc import ABC
from logging import Logger
from ssl import SSLContext
from typing import *

from dataclasses import dataclass, field
from tornado.httputil import HTTPServerRequest
from tornado.web import Application, RequestHandler
from typing.re import *

from .idiscoverable import IDiscoverable
from .ihc import IHandlerController
from .iloggable import ILoggable
from .iresponder import IResponder
from .types import HandlerListType

@dataclass
class IApplication(Application, ILoggable, IDiscoverable, ABC):
    name: str
    responder_class: Type[IResponder]
    handlers: HandlerListType = field(default_factory=list)
    handler_controllers: List[IHandlerController] = field(default_factory=list)
    ssl_options: SSLContext = None
    
    def add_handler(self, pattern: Union[AnyStr, Pattern[Any]], handler_type: Type[RequestHandler], *params):
        pass
    def attach_handler_controller(self, controller: IHandlerController):
        pass
    def normalize_request(self, request: HTTPServerRequest) -> HTTPServerRequest:
        return request
    
    #region Start server
    def run(self, blocking=True, num_processes=1):
        """
        Runs the server on the port specified earlier.
        Server blocks the IO.
        """
        pass
    
    @classmethod
    def simple_start_decorator_with_settings(cls, **settings):
        """
        Decorator creator with settings.
        
        Resulting decorator turns function into the simple server start method.
        It initializes logging and ConfigLoader in the soft-mode,
        than initializes the class instance, runs this function and starts the server.
        
        :param settings:
        Settings used for the server initialization
        :return:
        The decorator to the function to start the server
        
        Example usage:
        @ApplicationBase.simple_start_decorator_with_settings(port=8123, static_files='static', debug=True)
        def my_func(server_app):
            server_app.logger.debug(f"{self.name}: I am going to be run")
        
        """
        return lambda func: cls.simple_start_decorator(func, **settings)
    
    @classmethod
    def simple_start_decorator(cls, pre_run_func: Callable[['IApplication', Any], None], **settings) -> Callable[[Any], None]:
        """
        Decorator that turn function into the simple server start method.
        It initializes logging and ConfigLoader in the soft-mode,
        than initializes the class instance, runs this function and starts the server.
        
        :param pre_run_func:
        Function to be run after the server initialization but before actual start.
        Any arguments are allowed.
        :param settings:
        Settings used for the server initialization
        :return:
        The function to start the server
        """
        
        def wrapper(*args, **kwargs):
            cls.simple_start_server(lambda server_application: pre_run_func(server_application, *args, **kwargs), **settings)
        return wrapper
    
    @classmethod
    def simple_start_prepare(cls) -> Logger:
        pass
    @classmethod
    def simple_start_server(cls, pre_run_func: Union[Callable[['IApplication'], None], None] = None, **settings):
        """
        Initializes logging and ConfigLoader in the soft-mode,
        than initializes the class instance, runs this function and starts the server.
        
        :param pre_run_func:
        Function to be run after the server initialization but before actual start.
        Must take only one argument - the server instance.
        :param settings:
        Settings used for the server initialization
        """
        
        pass
    #endregion

__all__ = \
[
    'IApplication',
]
