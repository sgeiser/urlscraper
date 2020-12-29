from dataclasses import dataclass, field
from enum import Enum, auto
from typing import *

from http_server_base.model import DataClassJsonEncoder
from http_server_base.subrequest_client import SubrequestClient, SimpleSubrequestClient
from http_server_base.tools import HttpSubrequest, SubrequestFailedError, HttpSubrequestResponse
from .auth_providers import AuthorizationProvider
from .oauth2_model import *

class RefreshPolicy(Enum):
    Disabled = auto()
    Expiring = auto()
    Expired = auto()

@dataclass
class OAuth2AuthorizationProvider(AuthorizationProvider):
    client_id: str
    client_secret: str
    
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    refresh_url: Optional[str] = None
    redirect_uri: Optional[str] = None
    
    refresh_policy: RefreshPolicy = RefreshPolicy.Expiring
    token_data: Optional[OAuth2TokenData] = None
    subrequest_client: SubrequestClient = field(default_factory=SimpleSubrequestClient)
    
    async def add_request_auth(self, request: HttpSubrequest, **kwargs) -> HttpSubrequest:
        if (self.token_data is None):
            raise AssertionError(f"Unable to provide an authorization with a missing 'token_data'")
        
        if (self.refresh_policy == RefreshPolicy.Disabled or self.refresh_url is None and self.token_url is None):
            pass
        elif (self.refresh_policy == RefreshPolicy.Expiring and self.token_data.almost_expired):
            await self.renew_token()
        elif (self.refresh_policy == RefreshPolicy.Expired and self.token_data.is_expired):
            await self.renew_token()
        
        return await self.token_data.auth_provider.add_request_auth(request)
    
    async def renew_token(self):
        data = RefreshTokenRequestBody \
        (
            refresh_token = self.token_data.refresh_token,
            client_id = self.client_id,
            client_secret = self.client_secret,
            scope = self.token_data.scope,
        )
        await self.request_token(self.refresh_url or self.token_url, data)
    
    async def request_token_from_client_credentials(self, *, scope: Optional[List[str]] = None):
        data = ClientCredentialsTokenRequestBody \
        (
            client_id = self.client_id,
            client_secret = self.client_secret,
            scope = scope,
        )
        await self.request_token(self.token_url, data)
    
    async def request_token_from_auth_code(self, code: str):
        data = AuthorizationCodeTokenRequestBody \
        (
            code = code,
            client_id = self.client_id,
            client_secret = self.client_secret,
            redirect_uri = self.redirect_uri,
        )
        await self.request_token(self.token_url, data)
    
    async def request_token_from_password(self, username: str, password: str, *, scope: Optional[List[str]] = None):
        data = PasswordTokenRequestBody \
        (
            username = username,
            password = password,
            client_id = self.client_id,
            client_secret = self.client_secret,
            scope = scope,
        )
        await self.request_token(self.token_url, data)
    
    async def request_token(self, url: str, data: TokenRequestBody, **kwargs) -> OAuth2TokenData:
        if (data.client_id is not None and data.client_secret is not None):
            kwargs.setdefault('auth_mode', 'basic')
            kwargs.setdefault('auth_username', data.client_id)
            kwargs.setdefault('auth_password', data.client_secret)
        
        try:
            _, token_data = await self.subrequest_client.fetch_json_model(url, method='POST', model=OAuth2TokenData, encoder=DataClassJsonEncoder, body=data, encode_body='application/x-www-form-urlencoded', **kwargs)
        except SubrequestFailedError as e:
            if (e.response.code == 401):
                self.token_data = None
            raise
        else:
            self.token_data = token_data
        
        return token_data
    
    async def authorize_via_redirect_uri(self, state: Optional[str] = None, *, scope: Optional[List[str]] = None, response_type: str = 'code') -> HttpSubrequestResponse:
        data = AuthorizationRequest \
        (
            client_id = self.client_id,
            redirect_uri = self.redirect_uri,
            state = state,
            scope = scope,
            response_type = response_type,
        )
        resp = await self.subrequest_client.fetch(self.authorization_url, method='POST', model=OAuth2TokenData, encoder=DataClassJsonEncoder, body=data, encode_body='application/x-www-form-urlencoded')
        return resp


__all__ = \
[
    'RefreshPolicy',
    'OAuth2AuthorizationProvider',
]
