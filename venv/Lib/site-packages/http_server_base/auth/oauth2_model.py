from abc import ABC
from dataclasses import dataclass, field
from datetime import timedelta, datetime
from enum import Enum
from typing import *

from dataclasses_json import DataClassJsonMixin, config

from .auth_providers import BearerAuthorizationProvider

scope_field_meta = config(decoder=lambda s: s.split() if (s is not None) else None, encoder=lambda s: ' '.join(s) if (s is not None) else s)

@dataclass
class OAuth2TokenData(DataClassJsonMixin):
    access_token: str
    token_type: str
    expires_in: Optional[timedelta] = field(default=None, metadata=config(decoder=lambda t: timedelta(seconds=t) if (t is not None) else None, encoder=lambda t: t.total_seconds() if (t is not None) else t))
    refresh_token: Optional[str] = None
    scope: Optional[List[str]] = field(default=None, metadata=scope_field_meta)
    
    acquire_time: datetime = field(init=False, default_factory=datetime.now)
    almost_expired_time: timedelta = field(init=False, default=timedelta(minutes=5))
    
    @property
    def is_expired(self) -> bool:
        if (self.expires_in is None):
            return False
        else:
            return self.expiration_time > datetime.now()
    
    @property
    def almost_expired(self) -> bool:
        if (self.expires_in is None):
            return False
        else:
            return self.expiration_time > datetime.now() + self.almost_expired_time
    
    @property
    def expiration_time(self) -> Optional[datetime]:
        if (self.expires_in is None):
            return None
        else:
            return self.acquire_time + self.expires_in
    
    @property
    def auth_provider(self) -> BearerAuthorizationProvider:
        return BearerAuthorizationProvider(access_token=self.access_token, token_type=self.token_type)


@dataclass
class AuthorizationRequest(DataClassJsonMixin):
    client_id: str
    response_type: str = 'code'
    state: Optional[str] = None
    redirect_uri: Optional[str] = None
    scope: Optional[List[str]] = field(default=None, metadata=scope_field_meta)


class TokenGrantType(Enum):
    Password = 'password'
    ClientCredentials = 'client_credentials'
    AuthorizationCode = 'authorization_code'
    RefreshToken = 'refresh_token'

class TokenRequestBody(DataClassJsonMixin, ABC):
    grant_type: TokenGrantType
    client_id: Optional[str]
    client_secret: Optional[str]

@dataclass
class PasswordTokenRequestBody(TokenRequestBody):
    username: str
    password: str
    
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[List[str]] = field(default=None, metadata=scope_field_meta)
    
    grant_type: TokenGrantType = field(init=False, default=TokenGrantType.Password)

@dataclass
class ClientCredentialsTokenRequestBody(TokenRequestBody):
    client_id: str
    client_secret: str
    scope: Optional[List[str]] = field(default=None, metadata=scope_field_meta)
    
    grant_type: TokenGrantType = field(init=False, default=TokenGrantType.ClientCredentials)

@dataclass
class AuthorizationCodeTokenRequestBody(TokenRequestBody):
    code: str
    redirect_uri: Optional[str] = None
    
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    grant_type: TokenGrantType = field(init=False, default=TokenGrantType.AuthorizationCode)

@dataclass
class RefreshTokenRequestBody(TokenRequestBody):
    refresh_token: str
    
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[List[str]] = field(default=None, metadata=scope_field_meta)
    
    grant_type: TokenGrantType = field(init=False, default=TokenGrantType.RefreshToken)


__all__ = \
[
    'AuthorizationCodeTokenRequestBody',
    'AuthorizationRequest',
    'ClientCredentialsTokenRequestBody',
    'OAuth2TokenData',
    'PasswordTokenRequestBody',
    'RefreshTokenRequestBody',
    'TokenGrantType',
    'TokenRequestBody',
]
