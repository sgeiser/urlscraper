from abc import ABC
from dataclasses import dataclass

from http_server_base.tools import HttpSubrequest
from .auth_providers import AuthorizationProvider

@dataclass
class ApiKeyAuthorizationProvider(AuthorizationProvider, ABC):
    name: str
    api_key: str

@dataclass
class QueryApiKeyAuthorizationProvider(ApiKeyAuthorizationProvider):
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        request.encode_query(query={ self.name: self.api_key })
        return request

@dataclass
class HeaderApiKeyAuthorizationProvider(ApiKeyAuthorizationProvider):
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        request.headers.setdefault(self.name, self.api_key)
        return request

@dataclass
class CookieApiKeyAuthorizationProvider(ApiKeyAuthorizationProvider):
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        request.headers.add('Cookie', f'{self.name}={self.api_key}')
        return request


__all__ = \
[
    'ApiKeyAuthorizationProvider',
    'CookieApiKeyAuthorizationProvider',
    'HeaderApiKeyAuthorizationProvider',
    'QueryApiKeyAuthorizationProvider',
]
