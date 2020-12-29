from abc import ABC
from dataclasses import Field
from enum import Enum
from typing import *

from functional import Option, Some

ALLOWED_HTTP_METHODS = \
[
    'get',
    'put',
    'post',
    'delete',
    'options',
    'head',
    'patch',
    'trace',
]

class Model(ABC):
    pass

T = TypeVar('T')
Z = TypeVar('Z')
class Filter(Generic[T], ABC):
    
    def check_value(self, value: T) -> bool:
        raise NotImplementedError
    
    @property
    def decoder(self) -> Optional[Callable[[Z], T]]:
        raise NotImplementedError
    @property
    def encoder(self) -> Optional[Callable[[T], Z]]:
        raise NotImplementedError
    def decode(self, value: Z) -> T:
        raise NotImplementedError
    def encode(self, value: T) -> Z:
        raise NotImplementedError
    
    @classmethod
    def empty(cls) -> Optional['Filter[T]']:
        raise NotImplementedError
    
    @property
    def is_empty(self) -> bool:
        raise NotImplementedError
    
    def mix_with(self, f: 'Filter[T]') -> 'Filter[T]':
        raise NotImplementedError

# region Traits
class HavingId(Model, ABC):
    @property
    def id(self) -> str:
        raise NotImplementedError

class HavingDescription(Model, ABC):
    description: Optional[str]

class HavingExtendedDescription(HavingDescription, ABC):
    summary: Optional[str]
    example: Optional[str]

class HavingPath(Model, ABC):
    name: str
    path: str
    pretty_path: str
    is_top_level: bool
    
    def recursive_update(self, mapping: Callable[['HavingPath', 'HavingPath'], Any], *, ignore_top_level: bool = True):
        raise NotImplementedError

class HavingValue(Model, Generic[T], ABC):
    default: Option[T]
    filter: Optional[Filter[T]]

class HavingStyle(Model, Generic[T], ABC):
    style: Optional[str]
    explode: bool
    allow_reserved: bool

class HavingExternalDocs(Model, ABC):
    external_docs: Optional['ModelExternalDocumentation']
# endregion

# region Helper Definitions
class ModelContact(Model, ABC):
    name: Optional[str]
    url: Optional[str]
    email: Optional[str]

class ModelLicence(Model, ABC):
    name: str
    url: Optional[str]

class ModelServerVariable(HavingValue[str], HavingDescription, ABC):
    default: Some[str]

class ModelExternalDocumentation(HavingDescription, ABC):
    url: str

class ModelServer(HavingDescription, ABC):
    url: str
    variables: Optional[Dict[str, ModelServerVariable]]

class ModelTag(HavingDescription, HavingExternalDocs, ABC):
    name: str
# endregion

# region Definitions
class ModelEnumData(HavingExtendedDescription, HavingPath, Generic[T], ABC):
    possible_values: List[T]
    base_class: Union['ModelClass', Type[T]]
    
    def check_value(self, value: T) -> bool:
        raise NotImplementedError

class ModelSchema(HavingId, HavingValue[T], HavingExtendedDescription, Generic[T], ABC):
    property_name: Optional[str]
    property_format: Optional[str]
    
    nullable: bool
    read_only: bool
    write_only: bool
    
    cls: Union['ModelClass', ModelEnumData, Type[T]]
    
    @property
    def metadata(self) -> Dict[str, 'ModelSchema']:
        raise NotImplementedError
    @property
    def as_field(self) -> Field:
        raise NotImplementedError

class ModelClass(HavingId, HavingExtendedDescription, HavingPath, ABC):
    properties: Dict[str, ModelSchema]
    required_properties: List[str]
    additional_properties: Union[bool, ModelSchema]
    
    parents: List['ModelClass']
    merged: bool
    
    @property
    def all_properties_iter(self) -> Iterator[Tuple[str, ModelSchema]]:
        raise NotImplementedError
    @property
    def all_properties(self) -> Dict[str, ModelSchema]:
        raise NotImplementedError
    
    @property
    def all_required_properties_iter(self) -> Iterator[str]:
        raise NotImplementedError
    @property
    def all_required_properties(self) -> List[str]:
        raise NotImplementedError

class ParameterType(Enum):
    Query = 'query'
    Header = 'header'
    Path = 'path'
    Cookie = 'cookie'

class ModelEncodingObject(HavingStyle, ABC):
    content_type: str
    headers: Optional[Dict[str, 'ModelParameter']]

class ModelMediaTypeObject(Model, ABC):
    schema: Optional[ModelSchema]
    example: Option[T]
    examples: Optional[Dict[str, T]]
    encoding: Optional[Dict[str, ModelEncodingObject]]

class ModelParameter(HavingId, HavingDescription, HavingStyle, HavingPath, Generic[T], ABC):
    name: str
    required: bool
    parameter_type: ParameterType
    
    deprecated: bool
    allow_empty_value: bool
    
    schema: Optional[ModelSchema]
    content: Optional[Dict[str, ModelMediaTypeObject]]
    example: Option[T]
    examples: Optional[Dict[str, T]]

class ModelRequestBodyObject(HavingDescription, HavingPath, ABC):
    content: Dict[str, ModelMediaTypeObject]
    required: bool

class ModelResponseObject(HavingDescription, HavingPath, ABC):
    # headers: Optional[Dict[str, ModelParameter]]
    content: Optional[Dict[str, ModelMediaTypeObject]]
    # links: Optional[Dict[str, ModelLinkObject]] # ignored
    
    @property
    def regular_request_parser(self) -> Tuple[str, Optional[ModelMediaTypeObject]]:
        raise NotImplementedError

class ModelEndpoint(HavingId, HavingExtendedDescription, HavingExternalDocs, HavingPath, ABC):
    tags: Optional[List[str]]
    external_docs: Optional[ModelExternalDocumentation]
    operation_id: Optional[str]
    request_body: Optional[ModelRequestBodyObject]
    responses: Dict[str, ModelResponseObject]
    default_response: Optional[ModelRequestBodyObject]
    callbacks: Optional[Dict[str, 'ModelPath']] # ref may be here
    deprecated: bool
    security: Optional[List[Dict[str, List[str]]]]
    servers: Optional[List[ModelServer]]
    
    all_parameters: List[ModelParameter]
    own_parameters: List[ModelParameter]
    parent_parameters: List[ModelParameter]
    
    @property
    def regular_request_parser(self) -> Tuple[str, Optional[ModelMediaTypeObject]]:
        raise NotImplementedError
    @property
    def regular_response(self) -> Tuple[Optional[str], Optional[ModelResponseObject]]:
        raise NotImplementedError

class ModelPath(HavingId, HavingExtendedDescription, HavingPath, ABC):
    endpoints: Dict[str, ModelEndpoint]
    servers: Optional[ModelServer]
    parameters: List[ModelParameter]
    endpoint_path: str
# endregion

# region Security Definitions
class SecuritySchemeType(Enum):
    ApiKey = 'apiKey'
    HTTP = 'http'
    OAuth2 = 'oauth2'
    OpenIDConnect = 'openIdConnect'

class ModelSecurityScheme(HavingDescription, HavingPath, HavingId, ABC):
    type: SecuritySchemeType
    """ REQUIRED. The type of the security scheme. Valid values are "apiKey", "http", "oauth2", "openIdConnect". """

class ApiKeySecurityScheme(ModelSecurityScheme, ABC):
    key_name: str
    """ REQUIRED. The name of the header, query or cookie parameter to be used. """
    
    # parameter: in
    container: ParameterType
    """ REQUIRED. The location of the API key. Valid values are "query", "header" or "cookie". """

class HttpSecurityScheme(ModelSecurityScheme, ABC):
    scheme: str
    """
    REQUIRED. The name of the HTTP Authorization scheme to be used in the [Authorization header as defined in RFC7235](https://tools.ietf.org/html/rfc7235#section-5.1).
    The values used SHOULD be registered in the [IANA Authentication Scheme registry](https://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml).
    """
    
    bearer_format: Optional[str]
    """ A hint to the client to identify how the bearer token is formatted. Bearer tokens are usually generated by an authorization server, so this information is primarily for documentation purposes. """

class OAuthFlowsType(Enum):
    Implicit = 'implicit'
    """ Configuration for the OAuth Implicit flow """
    
    Password = 'password'
    """ Configuration for the OAuth Resource Owner Password flow """
    
    ClientCredentials = 'clientCredentials'
    """ Configuration for the OAuth Client Credentials flow. Previously called application in OpenAPI 2.0. """
    
    AuthorizationCode = 'authorizationCode'
    """ Configuration for the OAuth Authorization Code flow. Previously called accessCode in OpenAPI 2.0. """

class ModelOAuthFlow(Model, ABC):
    type: OAuthFlowsType
    
    # Only: Implicit, AuthorizationCode
    authorization_url: str
    """ REQUIRED. The authorization URL to be used for this flow. This MUST be in the form of a URL. """

    # Only: Password, ClientCredentials, AuthorizationCode
    token_url: str
    """ REQUIRED. The token URL to be used for this flow. This MUST be in the form of a URL. """
    
    refresh_url: Optional[str]
    """ The URL to be used for obtaining refresh tokens. This MUST be in the form of a URL. """
    
    scopes: Dict[str, str]
    """
    REQUIRED. The available scopes for the OAuth2 security scheme.
    A map between the scope name and a short description for it. The map MAY be empty.
    """

class OAuth2SecurityScheme(ModelSecurityScheme, ABC):
    flows: Dict[OAuthFlowsType, ModelOAuthFlow]
    """ REQUIRED. An object containing configuration information for the flow types supported. """

class OpenIDConnectSecurityScheme(ModelSecurityScheme, ABC):
    open_id_connect_url: str
    """ REQUIRED. OpenId Connect URL to discover OAuth2 configuration values. This MUST be in the form of a URL. """
# endregion
# region Meta Information
class OpenApiInfo(HavingDescription, ABC):
    title: str
    version: str
    terms_of_service: Optional[str]
    contact: Optional[ModelContact]
    licence: Optional[ModelLicence]

class OpenApiMetadata(HavingExternalDocs, HavingId, ABC):
    name: str
    openapi: str
    info: OpenApiInfo
    
    servers: List[ModelServer]
    tags: Optional[List[ModelTag]]
    security: Optional[List[Dict[str, List[str]]]]
# endregion


__all__ = \
[
    'ALLOWED_HTTP_METHODS',
    
    'ApiKeySecurityScheme',
    'Filter',
    'HavingDescription',
    'HavingExtendedDescription',
    'HavingExternalDocs',
    'HavingId',
    'HavingPath',
    'HavingStyle',
    'HavingValue',
    'HttpSecurityScheme',
    'Model',
    'ModelClass',
    'ModelContact',
    'ModelEncodingObject',
    'ModelEndpoint',
    'ModelEnumData',
    'ModelExternalDocumentation',
    'ModelLicence',
    'ModelMediaTypeObject',
    'ModelOAuthFlow',
    'ModelParameter',
    'ModelPath',
    'ModelRequestBodyObject',
    'ModelResponseObject',
    'ModelSchema',
    'ModelSecurityScheme',
    'ModelServer',
    'ModelServerVariable',
    'ModelTag',
    'OAuth2SecurityScheme',
    'OAuthFlowsType',
    'OpenApiInfo',
    'OpenApiMetadata',
    'OpenIDConnectSecurityScheme',
    'ParameterType',
    'SecuritySchemeType',
]
