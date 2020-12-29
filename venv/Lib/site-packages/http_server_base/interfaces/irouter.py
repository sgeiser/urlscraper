from abc import ABC
from typing import *

from dataclasses import dataclass, field
from tornado.httputil import HTTPServerRequest, HTTPMessageDelegate
from tornado.routing import Rule, Matcher, RuleRouter, PathMatches
from tornado.web import RequestHandler
from typing.re import *

from .iapplication import IApplication
from .iloggable import ILoggable
from .types import HandlerType

@dataclass
class Handler:
    handler_type: Type[RequestHandler]
    params: Dict[str, Any] = field(default_factory=dict)
    match_args: List[Any] = field(default_factory=list)

@dataclass
class IRouter(RuleRouter, Rule, Matcher, ILoggable, ABC):
    app: IApplication
    owner: ILoggable = None
    name: str = 'router'
    
    logger_name: str = None
    def __post_init__(self):
        if (self.owner is None):
            self.owner = self.app
        self.initialize_logger()
    
    def initialize_logger(self, *args, **kwargs):
        if (self.logger_name is None):
            self.logger_name = f'{self.owner.logger_name}.{self.name}'
        super().initialize_logger(*args, **kwargs)
    
    def unwrap_rule(self, rule: Union[HandlerType, Rule]) -> HandlerType:
        if (not isinstance(rule, Rule)):
            return rule
        
        if (isinstance(rule.matcher, PathMatches)):
            return rule.matcher.regex, rule.target, rule.target_kwargs
        else:
            raise ValueError(f"Cannot unwrap rule, unsupported matcher type: '{type(rule.matcher)}', expected: PathMatches")
    def add_rules(self, rules: List[Union[HandlerType, Rule]], **kwargs):
        for rule in rules:
            pattern, handler, *params = self.unwrap_rule(rule)
            self.add_handler(pattern, handler, *params, **kwargs)
    def add_handler(self, pattern: Union[AnyStr, Pattern[AnyStr]], handler_type: Type[RequestHandler], *params, **kwargs) -> Handler:
        pass
    
    @property
    def matcher(self):
        return self
    @property
    def target(self):
        return self
    
    def match(self, request: HTTPServerRequest, **kwargs) -> Optional[Dict[str, Any]]:
        m = self._match(request, **kwargs)
        if (m is not None):
            return m.params
    
    def find_handler(self, request: HTTPServerRequest, **kwargs) -> Optional[HTTPMessageDelegate]:
        m = self._match(request, **kwargs)
        if (m is not None):
            args = m.match_args
            if (args is None):
                args = [ request.path.encode() ]
            return self.app.get_handler_delegate(request, target_class=m.handler_type, target_kwargs=m.params, path_args=args)
    
    def _match(self, request: HTTPServerRequest, **kwargs) -> Optional[Handler]:
        raise NotImplementedError

__all__ = \
[
    'Handler',
    'IRouter',
]
