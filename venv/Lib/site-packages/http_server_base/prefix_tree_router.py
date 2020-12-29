import re
from typing import *

from dataclasses import dataclass, field, InitVar, replace
from tornado.httputil import HTTPServerRequest
from tornado.web import RequestHandler
from typing.re import *

from .interfaces import Handler, IRouter
from .tools.prefix_tree_map import PrefixTreeMap

@dataclass
class PrefixTreeRouter(IRouter):
    escape_options = [ '/', '?', '(|/.*)', '(|(/.*))', '.*', '(.*)', '$' ]
    unescape_endings_pattern = fr'\^?(.*?[^\\])({"|".join(re.escape(opt) for opt in escape_options)})*$', r'\1'
    unescape_group_pattern = r'(^|[^\\])\(([^|]*[^\\])\)', r'\1\2'
    unescape_escape_pattern = r'\\(.)', r'\1'
    unescapes = [ unescape_endings_pattern, unescape_group_pattern, unescape_escape_pattern ]
    
    tree: PrefixTreeMap[Handler] = field(init=False, default_factory=PrefixTreeMap)
    optimize_tree: InitVar[bool] = False
    last_key: Optional[str] = field(init=False, repr=False, default=None)
    last_value: Optional[Handler] = field(init=False, repr=False, default=None)
    
    # noinspection PyMethodOverriding
    def __post_init__(self, optimize_tree: bool):
        super().__post_init__()
        
        for h in self.app.handlers:
            self.add_handler(*h)
        
        if (optimize_tree):
            self.optimize()
    
    def add_handler(self, pattern: Union[AnyStr, Pattern[str]], handler_type: Type[RequestHandler], *params, **kwargs) -> Handler:
        handler = Handler(handler_type, *params)
        key, match_arg = self.unescape(pattern)
        self._register_handler(key, handler, match_arg=match_arg)
        return handler
    
    def unescape(self, pattern: Union[AnyStr, Pattern[str]]) -> Tuple[str, str]:
        if (isinstance(pattern, Pattern)):
            pattern = pattern.pattern
        if (isinstance(pattern, bytes)):
            pattern = pattern.decode()
        
        pattern = re.sub(*self.unescape_endings_pattern, pattern)
        match_arg = None
        _m = re.search(self.unescape_group_pattern[0], pattern)
        if (_m is not None):
            match_arg = pattern[:_m.end(1)].rstrip(self.tree.separator)
        _pattern = None
        while (pattern != _pattern):
            _pattern = pattern
            pattern = re.sub(*self.unescape_group_pattern, pattern)
        pattern = re.sub(*self.unescape_escape_pattern, pattern)
        
        pattern = pattern.rstrip(self.tree.separator)
        return pattern, match_arg
    
    def _register_handler(self, key: str, handler: Handler, *, match_arg: str = None):
        if (match_arg is None):
            match_arg = key
        key = key.rstrip(self.tree.separator)
        self.logger.debug(f"Registering handler '{key}' => '{handler.handler_type.__name__}' (match_arg='{match_arg}')")
        handler.match_args.insert(0, match_arg)
        self.tree.add(key, handler)
        self.last_key = None
    
    def optimize(self):
        self.tree.optimize()
    
    def get_key(self, request: HTTPServerRequest, **kwargs) -> str:
        return request.path.rstrip(self.tree.separator)
    
    def _match(self, request: HTTPServerRequest, **kwargs) -> Optional[Handler]:
        key = self.get_key(request, **kwargs)
        if (key == self.last_key):
            return self.last_value
        
        result = self.tree.get(key, None)
        self.logger.debug(f"Matching path '{key}' => {result}")
        self.last_value = result
        if (result is not None):
            _sep = self.tree.separator
            offset = _sep.join(key.split(_sep)[len(result.match_args[0].split(_sep)):])
            self.logger.trace(f"Offset: '{offset}' (match_args[0]='{result.match_args[0]}')")
            # noinspection PyArgumentList
            result: Handler = replace(result, match_args=[ offset, *result.match_args[1:] ])
        return result

__all__ = \
[
    'PrefixTreeRouter',
]
