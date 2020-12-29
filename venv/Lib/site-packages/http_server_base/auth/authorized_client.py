from typing import *

from tornado.httpclient import HTTPRequest

from http_server_base.subrequest_client import SubrequestClient
from http_server_base.tools import HttpSubrequest
from .auth_providers import AuthorizationProvider

class AuthorizedClient(SubrequestClient):
    auth_provider: Optional[AuthorizationProvider] = None
    
    async def _fetch__form_request(self, request: Union[str, HTTPRequest], *, authorization: Optional[AuthorizationProvider] = None, auth_required: bool = False, **kwargs) -> HttpSubrequest:
        request = await super()._fetch__form_request(request, **kwargs)
        request = await self._fetch__form_request__add_authorization(request, authorization=authorization, auth_required=auth_required, **kwargs)
        return request
    
    async def _fetch__form_request__add_authorization(self, request: HttpSubrequest, *, authorization: Optional[AuthorizationProvider], auth_required: bool, **kwargs) -> HttpSubrequest:
        if (authorization is None):
            authorization = self.auth_provider
        
        if (authorization is not None):
            request = await authorization.add_request_auth(request, **kwargs)
        elif (auth_required):
            raise ValueError("Authorization was required but not provided")
        
        return request


__all__ = \
[
    'AuthorizedClient',
]
