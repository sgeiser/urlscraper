from typing import *

from typing.re import *

from http_server_base.interfaces import Handler
from http_server_base.prefix_tree_router import PrefixTreeRouter
from .base_rest_request_handler import BaseRest_RequestHandler
from .interfaces import IRest_RequestHandler

class PrefixTreeRestRouter(PrefixTreeRouter):
    def add_handler(self, *params, **kwargs) -> Handler:
        x, *other = params
        if (isinstance(x, (str, Pattern))):
            t, *other = other
        else:
            t = x
        
        if (isinstance(t, type) and issubclass(t, IRest_RequestHandler)):
            return self.add_rest_handler(t, *other, **kwargs)
        else:
            return super().add_handler(*params, **kwargs)
    
    def add_rest_handler(self, handler_type: Type[IRest_RequestHandler], *params, **kwargs) -> Handler:
        if (not issubclass(handler_type, BaseRest_RequestHandler)):
            raise TypeError("IRest_RequestHandler subclasses other than BaseRest_RequestHandler are not supported")
        self.logger.debug(f"Adding REST handler: '{handler_type.__name__}'")
        handler_type: Type[BaseRest_RequestHandler]
        
        handler = Handler(handler_type, *params)
        base_path = handler_type.base_path.rstrip('/')
        if (not base_path and len(params) > 0 and isinstance(params[0], dict) and 'base_path' in params[0]):
            base_path = params[0]['base_path']
        
        for _, path in handler_type.in_request_router_class.get_class_endpoints(handler_type):
            path = base_path + path
            self.logger.trace(f"Registering endpoint '{path}'")
            self._register_handler(path, handler)
        
        return handler

__all__ = \
[
    'PrefixTreeRestRouter',
]
