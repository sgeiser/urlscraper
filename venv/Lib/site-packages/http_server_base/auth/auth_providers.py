from abc import ABC
from dataclasses import dataclass

from http_server_base.tools import HttpSubrequest

class AuthorizationProvider(ABC):
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        raise NotImplementedError

@dataclass
class BasicAuthorizationProvider(AuthorizationProvider):
    username: str
    password: str
    
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        request.auth_mode = 'basic'
        request.auth_username = self.username
        request.auth_password = self.password
        return request

@dataclass
class BearerAuthorizationProvider(AuthorizationProvider):
    access_token: str
    token_type: str = 'bearer'
    
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        request.auth_mode = None
        request.auth_username = None
        request.auth_password = None
        request.headers.setdefault('Authorization', f'{self.token_type.title()} {self.access_token}')
        return request


__all__ = \
[
    'AuthorizationProvider',
    'BearerAuthorizationProvider',
    'BasicAuthorizationProvider',
]
