from .base_rest_request_handler import BaseRest_RequestHandler
from .path_tree_in_request_router import  PathTreeInRequestRouter

class PathTreeRest_RequestHandler(BaseRest_RequestHandler):
    in_request_router_class = PathTreeInRequestRouter

__all__ = \
[
    'PathTreeRest_RequestHandler',
]
