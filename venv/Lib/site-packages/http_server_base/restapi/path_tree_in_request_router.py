from http_server_base.tools.path_tree_map import PathTreeMap
from .base_in_request_router import BaseInRequestRouter
from .interfaces import Endpoint

class PathTreeInRequestRouter(BaseInRequestRouter[PathTreeMap, str]):
    mapper_type = PathTreeMap[Endpoint[str]]

__all__ = \
[
    'PathTreeInRequestRouter',
]
