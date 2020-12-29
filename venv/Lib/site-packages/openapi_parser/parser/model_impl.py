from abc import ABC
from dataclasses import Field, dataclass, field
from typing import *
from typing import Type, Dict, Union, Any

from dataclasses_json import dataclass_json, LetterCase, config, DataClassJsonMixin
from functional import Option, OptionNone, Some
from typing.re import *

from openapi_parser.model import *
from openapi_parser.util.typing_proxy import GenericProxy
from openapi_parser.util.utils import SearchableEnum
from .filters import *
from .path import *
# region Schemas & Classes
from ..model import SecuritySchemeType

METADATA_KEY = 'openapi-parser'

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelClassImpl(ModelClass, HavingPathImpl, DataClassJsonMixin):
    properties: Dict[str, Union[ModelSchema, Any]] = field(compare=False, hash=False)
    required_properties: List[str] = field(default_factory=list, metadata=config(field_name='required'))
    additional_properties: Union[bool, Union[ModelSchema, Any]] = True
    
    description: Optional[str] = None
    summary: Optional[str] = field(default=None, metadata=config(field_name='title'))
    example: Optional[str] = None
    
    parents: List[ModelClass] = field(init=False, default_factory=list)
    merged: bool = field(init=False, default=False)
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        yield from self.properties.values()
    
    @property
    def all_properties_iter(self) -> Iterator[Tuple[str, ModelSchema]]:
        for p in self.parents:
            yield from p.all_properties_iter
        yield from self.properties.items()
    @property
    def all_properties(self) -> Dict[str, ModelSchema]:
        return dict(self.all_properties_iter)
    
    @property
    def all_required_properties_iter(self) -> Iterator[str]:
        for p in self.parents:
            yield from p.all_required_properties_iter
        yield from self.required_properties
    @property
    def all_required_properties(self) -> List[str]:
        return list(self.all_required_properties_iter)
    
    @property
    def id(self) -> str:
        return self.name

@dataclass
class ClassRef:
    class_path: str
    class_model: ModelClass

@dataclass
class ForwardRef(ClassRef):
    @property
    def class_model(self) -> ModelClass:
        raise ValueError(f"Attempt to load forward-ref '{self.class_path}'")

class PropertyType(SearchableEnum):
    Integer = 'integer'
    Number  = 'number'
    Boolean = 'boolean'
    String  = 'string'
    Array   = 'array'
    Object  = 'object'

MISSING = object()

T = TypeVar('T')
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelEnumDataImpl(ModelEnumData, HavingPathImpl, Generic[T]):
    possible_values: List[T] = field(metadata=config(field_name='enum'))
    base_class: Union[ModelClass, Type[T]] = field(init=False)
    
    description: Optional[str] = None
    summary: Optional[str] = None
    example: Optional[str] = None
    
    def check_value(self, value: T) -> bool:
        return value in self.possible_values
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        yield self.base_class
    
    @property
    def is_top_level(self) -> bool:
        return False

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelSchemaImpl(ModelSchema, DataClassJsonMixin, Generic[T]):
    property_name: str = field(init=False)
    property_type: Optional[PropertyType] = field(default=None, metadata=config(field_name='type'))
    property_format: Optional[str] = field(default=None, metadata=config(field_name='format'))
    description: Optional[str] = None
    summary: Optional[str] = field(default=None, metadata=config(field_name='title'))
    example: Optional[str] = None
    
    default: Option[T] = field(default=OptionNone)
    nullable: bool = False
    read_only: bool = False
    write_only: bool = False
    
    filter: Filter[T] = field(init=False, default_factory=EmptyFilter)
    cls: Union[ModelClass, ModelEnumData, Type[T]] = field(init=False, default=Any)
    
    def __post_init__(self):
        if (not Option.is_option(self.default)):
            self.default = Some(self.default)
    
    @property
    def metadata(self) -> Dict[str, ModelSchema]:
        return { METADATA_KEY: self }
    
    @property
    def as_field(self) -> Field:
        kwargs = dict()
        if (self.default.non_empty):
            kwargs['default'] = self.default
        
        f = field(metadata=config(metadata=self.metadata, encoder=self.filter.encoder, decoder=self.filter.decoder), **kwargs)
        f.type = self.cls
        return f
    
    @property
    def id(self) -> str:
        return self.property_name


def extract_metadata(f: Field) -> ModelSchema:
    return f.metadata[METADATA_KEY]
# endregion
# region Helpers
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelExternalDocumentationImpl(ModelExternalDocumentation, DataClassJsonMixin):
    url: str
    description: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelServerVariableImpl(ModelServerVariable, DataClassJsonMixin):
    default: Some[str] = field(metadata=config(decoder=Some))
    filter: Optional[ModelEnumData[T]] = field(init=False, default=None)
    description: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelServerImpl(ModelServer, DataClassJsonMixin):
    url: str
    description: Optional[str] = None
    variables: Optional[Dict[str, ModelServerVariableImpl]] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelContactImpl(ModelContact, DataClassJsonMixin):
    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelLicenceImpl(ModelLicence, DataClassJsonMixin):
    name: str
    url: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelTagImpl(ModelTag, DataClassJsonMixin):
    name: str
    description: Optional[str] = None
    external_docs: Optional[ModelExternalDocumentationImpl] = None


# endregion
# region Endpoints
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelEncodingObjectImpl(ModelEncodingObject, DataClassJsonMixin):
    content_type: str
    headers: Optional[Dict[str, 'ModelParameter']]
    
    style: Optional[str] = None
    explode: bool = OptionNone
    allow_reserved: bool = False
    
    def __post_init__(self):
        if (self.explode is OptionNone):
            self.explode = self.style == 'form'

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelMediaTypeObjectImpl(ModelMediaTypeObject, DataClassJsonMixin):
    schema: Optional[ModelSchema] = None
    example: Option[T] = OptionNone
    examples: Optional[Dict[str, T]] = None
    encoding: Optional[Dict[str, ModelEncodingObjectImpl]] = None
    
    def __post_init__(self):
        if (not isinstance(self.example, Option)):
            self.example = Some(self.example)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelResponseObjectImpl(ModelResponseObject, HavingPathImpl, DataClassJsonMixin):
    description: str
    # headers: Optional[Dict[str, ModelParameter]]
    content: Optional[Dict[str, ModelMediaTypeObjectImpl]] = None
    # links: Optional[Dict[str, ModelLinkObject]] # ignored
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        if (self.content is not None):
            for v in self.content.values():
                yield v.schema
    
    @property
    def regular_request_parser(self) -> Tuple[str, Optional[ModelMediaTypeObject]]:
        return find_default_parser(self.content)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelParameterImpl(ModelParameter, HavingPathImpl, Intermediate, DataClassJsonMixin):
    name: str = field(init=True)
    parameter_type: ParameterType = field(metadata=config(field_name='in'))
    description: Optional[str] = None
    
    required: bool = False
    deprecated: bool = False
    allow_empty_value: bool = False
    
    schema: Optional[ModelSchema] = None
    content: Optional[Dict[str, ModelMediaTypeObjectImpl]] = None
    example: Option[T] = OptionNone
    examples: Optional[Dict[str, T]] = None
    
    style: Optional[str] = None
    explode: bool = OptionNone
    allow_reserved: bool = False
    
    def __post_init__(self):
        if (self.explode is OptionNone):
            self.explode = self.style == 'form'
        if (not isinstance(self.example, Option)):
            self.example = Some(self.example)
    
    @property
    def id(self) -> str:
        return self.name
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        yield self.schema
        if (self.content is not None):
            for v in self.content.values():
                yield v.schema

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelRequestBodyObjectImpl(ModelRequestBodyObject, HavingPathImpl, DataClassJsonMixin):
    content: Dict[str, ModelMediaTypeObjectImpl]
    description: Optional[str] = None
    required: bool = False
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        if (self.content is not None):
            for v in self.content.values():
                yield v.schema

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelEndpointImpl(ModelEndpoint, HavingPathImpl, DataClassJsonMixin):
    responses: Dict[str, ModelResponseObject]
    tags: Optional[List[str]] = None
    external_docs: Optional[ModelExternalDocumentationImpl] = None
    operation_id: Optional[str] = None
    request_body: Optional[ModelRequestBodyObject] = None
    default_response: Optional[ModelResponseObject] = field(init=False)
    callbacks: Optional[Dict[str, 'ModelPath']] = None # ref may be here
    deprecated: bool = False
    security: Optional[Any] = None
    servers: Optional[ModelServerImpl] = None
    
    own_parameters: List[ModelParameter] = field(default_factory=list, metadata=config(field_name='parameters'))
    parent_parameters: List[ModelParameter] = field(init=False, default_factory=list)
    all_parameters: List[ModelParameter] = field(init=False, default_factory=list)
    
    description: Optional[str] = None
    summary: Optional[str] = None
    example: Optional[str] = field(init=False, default=None)
    
    @property
    def id(self) -> str:
        return self.operation_id
    
    @property
    def name(self) -> str:
        return self.operation_id
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        yield self.request_body
        yield self.default_response
        yield from self.responses.values()
        yield from self.own_parameters
    
    @property
    def regular_request_parser(self) -> Tuple[str, Optional[ModelMediaTypeObject]]:
        return find_default_parser(self.request_body.content)
    @property
    def regular_response(self) -> Tuple[Optional[str], Optional[ModelResponseObject]]:
        return find_default_response(self)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelPathImpl(ModelPath, HavingPathImpl, DataClassJsonMixin):
    endpoints: Dict[str, ModelEndpoint] = field(init=False, default_factory=dict)
    servers: Optional[ModelServerImpl] = None
    parameters: List[ModelParameter] = field(default_factory=list)
    
    description: Optional[str] = None
    summary: Optional[str] = None
    example: Optional[str] = field(init=False, default=None)
    
    endpoint_path: str = field(init=False)
    @property
    def id(self) -> str:
        return self.endpoint_path
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        yield from self.parameters
        yield from self.endpoints.values()
    
    @property
    def name(self) -> str:
        return self.endpoint_path

def find_default_response(endpoint: ModelEndpoint) -> Tuple[Optional[str], Optional[ModelResponseObject]]:
    for r in [ *map(str, range(200, 300)), '2xx', *map(str, range(300, 400)), '3xx', ]:
        if r in endpoint.responses:
            return r, endpoint.responses[r]
    
    if (endpoint.responses):
        # noinspection PyTypeChecker
        return list(endpoint.responses.items())[0]
    elif (endpoint.default_response):
        return None, endpoint.default_response
    else:
        return None, None

def find_default_parser(content: Optional[Dict[str, ModelMediaTypeObject]]) -> Tuple[str, Optional[ModelMediaTypeObject]]:
    if (not content):
        return '*/*', None
    
    for r in [ 'application/json', 'application/*', '*/*', ]:
        if r in content:
            return r, content[r]
    
    # noinspection PyTypeChecker
    return list(content.items())[0]
# endregion
# region Security Definitions
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelSecuritySchemeImpl(ModelSecurityScheme, HavingPathImpl, ABC):
    type: SecuritySchemeType = field(init=False, default=SecuritySchemeType.ApiKey)
    name: str = field(init=False)
    
    @property
    def id(self) -> str:
        return self.name
    
    def _child_items(self) -> Iterator[Union[Type, GenericProxy, ModelSchema, HavingPath, None]]:
        return ()
    
    @classmethod
    def _get_security_scheme_decoder(cls) -> Callable[[Dict[str, Any]], 'ModelSecuritySchemeImpl']:
        from .inheritance_support import discriminator_decoder
        return discriminator_decoder('type', { k.value: v for k, v in SECURITY_SCHEME_MAPPING.items() })
    
    _security_scheme_decoder: Callable[[Dict[str, Any]], 'ModelSecuritySchemeImpl'] = field(init=False, repr=False, compare=False, default=None)
    
    @classmethod
    def decode(cls, data: Dict[str, Any]) -> 'ModelSecuritySchemeImpl':
        if (cls._security_scheme_decoder is None):
            cls._security_scheme_decoder = cls._get_security_scheme_decoder()
        
        return cls._security_scheme_decoder(data)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ApiKeySecuritySchemeImpl(ApiKeySecurityScheme, ModelSecuritySchemeImpl):
    key_name: str = field(metadata=config(field_name='name'))
    container: ParameterType = field(metadata=config(field_name='in'))
    description: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class HttpSecuritySchemeImpl(HttpSecurityScheme, ModelSecuritySchemeImpl):
    scheme: str
    bearer_format: Optional[str]
    type: SecuritySchemeType = field(init=False, default=SecuritySchemeType.HTTP)
    description: Optional[str] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModelOAuthFlowImpl(ModelOAuthFlow):
    type: OAuthFlowsType = field(init=False)
    scopes: Dict[str, str]
    refresh_url: Optional[str] = field(default=None)
    
    _authorization_url: Optional[str] = field(default=None, metadata=config(field_name='authorizationUrl'))
    _token_url: Optional[str] = field(default=None, metadata=config(field_name='tokenUrl'))
    
    @property
    def authorization_url(self) -> str:
        """ Only for: Implicit, AuthorizationCode """
        
        if (self.type in (OAuthFlowsType.Implicit, OAuthFlowsType.AuthorizationCode)):
            return self._authorization_url
        else:
            # ToDo: Error class
            raise ValueError(f"Unable to get field 'authorization_url' for {type(self).__name__} of type {self.type}")
    
    @property
    def token_url(self) -> str:
        """ Only for: Password, ClientCredentials, AuthorizationCode """
        
        if (self.type in (OAuthFlowsType.Password, OAuthFlowsType.ClientCredentials, OAuthFlowsType.AuthorizationCode)):
            return self._token_url
        else:
            # ToDo: Error class
            raise ValueError(f"Unable to get field 'token_url' for {type(self).__name__} of type {self.type}")

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OAuth2SecuritySchemeImpl(OAuth2SecurityScheme, ModelSecuritySchemeImpl):
    flows: Dict[OAuthFlowsType, ModelOAuthFlowImpl]
    type: SecuritySchemeType = field(init=False, default=SecuritySchemeType.OAuth2)
    description: Optional[str] = None
    
    def __post_init__(self):
        for k, v in self.flows.items():
            v.type = k

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OpenIDConnectSecuritySchemeImpl(OpenIDConnectSecurityScheme, ModelSecuritySchemeImpl):
    open_id_connect_url: str
    type: SecuritySchemeType = field(init=False, default=SecuritySchemeType.OpenIDConnect)
    description: Optional[str] = None

SECURITY_SCHEME_MAPPING: Dict[SecuritySchemeType, Type[ModelSecuritySchemeImpl]] = \
{
    SecuritySchemeType.ApiKey:        ApiKeySecuritySchemeImpl,
    SecuritySchemeType.HTTP:          HttpSecuritySchemeImpl,
    SecuritySchemeType.OAuth2:        OAuth2SecuritySchemeImpl,
    SecuritySchemeType.OpenIDConnect: OpenIDConnectSecuritySchemeImpl,
}
""" Mapping between `SecuritySchemeType` and their implementation classes """
# endregion
# region OpenAPI Metadata
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OpenApiInfoImpl(OpenApiInfo, DataClassJsonMixin):
    title: str
    version: str
    description: Optional[str] = None
    terms_of_service: Optional[str] = None
    contact: Optional[ModelContactImpl] = None
    licence: Optional[ModelLicenceImpl] = field(default=None, metadata=config(field_name='license'))

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OpenApiMetadataImpl(OpenApiMetadata, DataClassJsonMixin):
    openapi: str
    info: OpenApiInfoImpl
    servers: List[ModelServerImpl] = field(default_factory=lambda: [ ModelServerImpl('/') ])
    tags: Optional[List[ModelTagImpl]] = None
    external_docs: Optional[ModelExternalDocumentationImpl] = None
    
    @property
    def id(self) -> str:
        return f'{self.info.title} v{self.info.version}'
    
    @property
    def name(self) -> str:
        return self.info.title
# endregion

__all__ = \
[
    'SECURITY_SCHEME_MAPPING',
    
    'ApiKeySecuritySchemeImpl',
    'ClassRef',
    'ForwardRef',
    'HavingPathImpl',
    'HttpSecuritySchemeImpl',
    'Intermediate',
    'ModelClassImpl',
    'ModelContactImpl',
    'ModelEncodingObjectImpl',
    'ModelEndpointImpl',
    'ModelEnumDataImpl',
    'ModelExternalDocumentationImpl',
    'ModelLicenceImpl',
    'ModelMediaTypeObjectImpl',
    'ModelOAuthFlowImpl',
    'ModelParameterImpl',
    'ModelPathImpl',
    'ModelRequestBodyObjectImpl',
    'ModelResponseObjectImpl',
    'ModelSchemaImpl',
    'ModelSecuritySchemeImpl',
    'ModelServerImpl',
    'ModelServerVariableImpl',
    'ModelTagImpl',
    'OAuth2SecuritySchemeImpl',
    'OpenApiInfoImpl',
    'OpenApiMetadataImpl',
    'OpenIDConnectSecuritySchemeImpl',
    'PropertyType',
    
    'extract_metadata',
    'find_default_parser',
    'find_default_response',
]

__pdoc_extras__ = \
[
    'SECURITY_SCHEME_MAPPING',
]
