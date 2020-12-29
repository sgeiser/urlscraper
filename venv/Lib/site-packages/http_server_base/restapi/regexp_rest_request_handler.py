from .base_rest_request_handler import BaseRest_RequestHandler
from .regexp_in_request_router import RegexpInRequestRouter

class RegexpRest_RequestHandler(BaseRest_RequestHandler):
    in_request_router_class = RegexpInRequestRouter

__all__ = \
[
    'RegexpRest_RequestHandler',
]
