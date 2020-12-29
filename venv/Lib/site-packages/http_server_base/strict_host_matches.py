from typing import *

from dataclasses import dataclass
from tornado.httputil import HTTPServerRequest, split_host_and_port
from tornado.routing import Matcher

from .tools.defaults import DEFAULT_PORTS

@dataclass
class StrictHostMatches(Matcher):
    """Matches requests from port specified by port regex."""
    protocol: str = None
    host: str = None
    port: int = None
    
    def match(self, request: HTTPServerRequest) -> Optional[dict]:
        host, port = split_host_and_port(request.host)
        if (self.protocol is not None and request.protocol != self.protocol):
            return None
        if (self.host is not None and host != self.host):
            return None
        if (self.port is not None and (port or DEFAULT_PORTS.get(request.protocol, None)) != self.port):
            return None
        
        return { }

__all__ = \
[
    'StrictHostMatches',
]
