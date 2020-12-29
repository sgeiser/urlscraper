from .base_in_request_router import *
from .base_rest_request_handler import *
from .interfaces import *
from .path_tree_in_request_router import *
from .path_tree_rest_request_handler import *
from .prefix_tree_rest_router import *
from .regexp_in_request_router import *
from .regexp_rest_request_handler import *

RestRouter = RegexpInRequestRouter
Rest_RequestHandler = RegexpRest_RequestHandler

simple_return = RestRouter.simple_return
encode_result = RestRouter.encode_result
rest_method = RestRouter.rest_method
extract_args = RestRouter.extract_args

__all__ = \
[
    'encode_result',
    'extract_args',
    'rest_method',
    'simple_return',
]
__pdoc__ = { }
__pdoc_extras__ = [ ]

submodules = \
[
    base_in_request_router,
    base_rest_request_handler,
    interfaces,
    path_tree_in_request_router,
    path_tree_rest_request_handler,
    prefix_tree_rest_router,
    regexp_in_request_router,
    regexp_rest_request_handler,
]

for _m in submodules: __all__.extend(_m.__all__)
from http_server_base.tools.docs import create_documentation_index
create_documentation_index(submodules, __name__, __pdoc__, __pdoc_extras__)
del create_documentation_index, submodules
