from typing import *

from tornado.web import RequestHandler
from typing.re import *
from typing.re import *

HandlerType = Union \
[
    Tuple[Union[str, Pattern[str]], Type[RequestHandler]],
    Tuple[Union[str, Pattern[str]], Type[RequestHandler], Dict[str, Any]],
]
HandlerListType = List[HandlerType]

__all__ = \
[
    'HandlerType',
    'HandlerListType',
]
__pdoc_extras__ = \
[
    'HandlerType',
    'HandlerListType',
]
