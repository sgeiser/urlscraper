import dataclasses
import datetime
import enum
import urllib.parse
import warnings
from functools import partial
from typing import *

import http_server_base
import http_server_base.auth
import http_server_base.model
import http_server_base.tools
import tornado.httpclient
from functional import Option, OptionNone, Some, tuple_transform
from http_server_base.auth import AuthorizedClient
from http_server_base.model import FilteringJsonEncoder

import openapi_parser.exporter.exporting_features.client
from openapi_parser.model import *
from openapi_parser.parser import OpenApiParser
from openapi_parser.util.naming_conventions import name_parts
from openapi_parser.util.utils import StrIO
from .abstract_writer import yielder, writer
from .footer_writer import FooterWriter
from .header_writer import HeaderWriter
from .inspect_writer import InspectWriter
from .method_writer import MethodWriter, MethodType

class ClientWriter(HeaderWriter, InspectWriter, MethodWriter, FooterWriter):
    @property
    def from_imports(self) -> Iterator[str]:
        imports =\
        [
            dataclasses.dataclass,
            dataclasses.field,
            datetime.date,
            datetime.datetime,
            datetime.time,
            enum.Enum,
            http_server_base.model.FilteringJsonEncoder,
            http_server_base.model.IEncoder,
            http_server_base.tools.filter_out_smart,
            http_server_base.tools.HttpSubrequest,
            http_server_base.tools.RequestLogger,
            tornado.httpclient.HTTPRequest,
            urllib.parse.ParseResult,
            urllib.parse.urlparse,
        ]
        other_imports = \
        [
            'typing.*',
            'http_server_base.auth.*',
            '.model.*',
            '.utils.datetime_decoder',
            '.utils.discriminator_decoder',
        ]
        
        yield from self.objects_to_from_imports(imports)
        yield from other_imports
    
    def parse_server_data(self, client_name: str, servers: List[ModelServer]) -> Option[Tuple[str, str, Iterator[str]]]:
        servers = [ s for s in servers if (s.url != '/') ]
        if (not servers):
            return OptionNone
        
        def _name_gen(s: ModelServer) -> Option[str]:
            return Option(s.description or s.url).map(self.enum_entry_name_pretty).map(self.object_valid_name_filter)
        
        default_server_name = _name_gen(servers[0]).get_or_else('Server1')
        enum_name = self.class_name_pretty(client_name + '-' + 'servers')
        def _gen() -> Iterator[str]:
            self.export(enum_name)
            yield f'class {enum_name}(Enum):'
            with self.indent():
                yield from self.inline_description(f"Enum-container of default servers used for `{client_name}`")
                for i, s in enumerate(servers):
                    s_name = _name_gen(s).get_or_else(f'Server{i + 1}')
                    yield f'{s_name} = {s.url!r}'
            yield
        
        return Some((enum_name, f'{enum_name}.{default_server_name}', _gen()))
    
    def dump_security_schema(self, security_schema: ModelSecurityScheme, *, flow: Optional[OAuthFlowsType] = None) -> Iterator[str]:
        method_name = self.method_name_pretty(f'provide_{security_schema.name}_authorization')
        
        tp: Type[http_server_base.auth.AuthorizationProvider]
        asynchronous: bool
        code: List[str]
        params: List[str]
        
        if (security_schema.type == SecuritySchemeType.ApiKey):
            security_schema: ApiKeySecurityScheme
            params = [ 'api_key: str' ]
            if (security_schema.container == ParameterType.Header):
                tp = http_server_base.auth.HeaderApiKeyAuthorizationProvider
            elif (security_schema.container == ParameterType.Query):
                tp = http_server_base.auth.QueryApiKeyAuthorizationProvider
            elif (security_schema.container == ParameterType.Cookie):
                tp = http_server_base.auth.CookieApiKeyAuthorizationProvider
            else:
                # ToDo: Warning
                warnings.warn(f"Security scheme of type '{security_schema.type}' (scheme '{security_schema.name}') has invalid value of property 'in': '{security_schema.container}'", UserWarning, 2)
                return
            
            asynchronous = False
            code = [ 'return ' + self.constructor(self.ref_name_pretty(tp), name=repr(security_schema.key_name), api_key='api_key') ]
        
        elif (security_schema.type == SecuritySchemeType.HTTP):
            security_schema: HttpSecurityScheme
            if (security_schema.scheme.lower() == 'basic'):
                tp = http_server_base.auth.BasicAuthorizationProvider
                params = [ 'username: str', 'password: str' ]
                constructor_params = dict(username='username', password='password')
            elif (security_schema.scheme.lower() == 'bearer'):
                tp = http_server_base.auth.BearerAuthorizationProvider
                params = [ 'access_token: str' ]
                constructor_params = dict(access_token='access_token')
            else:
                # ToDo: Warning
                warnings.warn(f"Scheme '{security_schema.scheme}' for security scheme of type '{security_schema.type}' (scheme '{security_schema.name}') is not supported", UserWarning, 2)
                return
            
            asynchronous = False
            code = [ 'return ' + self.constructor(self.ref_name_pretty(tp), **constructor_params) ]
        
        elif (security_schema.type == SecuritySchemeType.OAuth2):
            security_schema: OAuth2SecurityScheme
            if (flow not in security_schema.flows):
                # ToDo: Warning
                warnings.warn(f"Security scheme of type '{security_schema.type}' (scheme '{security_schema.name}') does not contain a flow: '{flow}'", UserWarning, 2)
                return
            else:
                flow_data = security_schema.flows[flow]
            if (len(security_schema.flows) > 1):
                method_name = self.method_name_pretty(f'{method_name}_{flow.value}_flow')
            
            tp = http_server_base.auth.OAuth2AuthorizationProvider
            if (flow == OAuthFlowsType.Password):
                grant_method = http_server_base.auth.OAuth2AuthorizationProvider.request_token_from_password
                params = [ 'username: str', 'password: str', '*', 'client_id: Optional[str] = None', 'client_secret: Optional[str] = None', 'scope: Optional[List[str]] = None' ]
                constructor_params = dict(client_id='client_id', client_secret='client_secret', token_url=repr(flow_data.token_url), refresh_url=repr(flow_data.refresh_url))
                grant_method_params = dict(username='username', password='password', scope='scope')
            elif (flow == OAuthFlowsType.ClientCredentials):
                grant_method = http_server_base.auth.OAuth2AuthorizationProvider.request_token_from_client_credentials
                params = [ 'client_id: str', 'client_secret: str', '*', 'scope: Optional[List[str]] = None' ]
                constructor_params = dict(client_id='client_id', client_secret='client_secret', token_url=repr(flow_data.token_url), refresh_url=repr(flow_data.refresh_url))
                grant_method_params = dict(scope='scope')
            elif (flow == OAuthFlowsType.AuthorizationCode):
                grant_method = http_server_base.auth.OAuth2AuthorizationProvider.authorize_via_redirect_uri
                params = [ 'state: str = None', 'redirect_uri: str = None', '*', 'client_id: Optional[str] = None', 'client_secret: Optional[str] = None', 'scope: Optional[List[str]] = None' ]
                constructor_params = dict(client_id='client_id', client_secret='client_secret', redirect_uri='redirect_uri', token_url=repr(flow_data.token_url), authorization_url=repr(flow_data.authorization_url), refresh_url=repr(flow_data.refresh_url))
                grant_method_params = dict(state='state', scope='scope')
            # elif (flow == OAuthFlowsType.Implicit):
            #     grant_method = http_server_base.auth.OAuth2AuthorizationProvider.request_token_from_auth_code
            #     params = [ 'redirect_uri: str', 'code: str', '*', 'client_id: Optional[str] = None', 'client_secret: Optional[str] = None' ]
            #     constructor_params = dict(client_id='client_id', client_secret='client_secret', redirect_uri='redirect_uri', authorization_url=repr(flow_data.authorization_url), repr(refresh_url=flow_data.refresh_url))
            #     grant_method_params = dict()
            else:
                # ToDo: Warning
                warnings.warn(f"Flow '{flow}' for security scheme of type '{security_schema.type}' (scheme '{security_schema.name}') is not supported", UserWarning, 2)
                return
            
            asynchronous = True
            code = \
            [
                'provider = ' + self.constructor(self.ref_name_pretty(tp), **constructor_params),
                'await ' + self.constructor(f'provider.{grant_method.__name__}', **grant_method_params),
                'return provider'
            ]
        
        else:
            # ToDo: Warning
            warnings.warn(f"Security scheme of type '{security_schema.type}' (scheme '{security_schema.name}') is not supported", UserWarning, 2)
            return
        
        yield from self.write_method_head(method_name, asynchronous=asynchronous, method_type=MethodType.RegularMethod, params=params, return_type=Some(self.ref_name_pretty(tp)))
        with self.indent():
            yield from self.smart_description(partial(self.generate_item_description, security_schema, item_type='security scheme'))
            yield from code
        yield
    
    def dump_client_authorization(self, parser: OpenApiParser) -> Iterator[str]:
        for path, s in parser.security_schemes.items():
            if (s.type == SecuritySchemeType.OAuth2):
                s: OAuth2SecurityScheme
                for flow in s.flows:
                    yield from self.dump_security_schema(s, flow=flow)
            else:
                yield from self.dump_security_schema(s)
    
    def dump_client_class(self, parser: OpenApiParser) -> Iterator[str]:
        package_name_parts = name_parts(parser.name)
        if (package_name_parts[-1] == 'client'):
            package_name_parts.pop(-1)
        
        package_name_parts.append('api')
        package_name_parts.append('client')
        client_name = self.class_name_pretty(parser.id_separator.join(package_name_parts))
        logger_name = f'{parser.name}.client'
        self.export(client_name)
        
        enum_name, default_server, enum_gen = tuple_transform(self.parse_server_data(client_name, parser.metadata.servers), 2)
        server_type = enum_name.map('Union[{}, str]'.format).get_or_else('str')
        if (enum_gen.non_empty):
            yield from enum_gen.get
        
        yield f"class {client_name}({self.ref_name_pretty(AuthorizedClient)}):"
        with self.indent():
            yield from self.smart_description(partial(self.generate_item_description, item=parser.metadata.info, item_type='client'))
            
            yield f'server: {server_type}'
            yield f'logger_name: str = {logger_name!r}'
            yield f'model_encoder: Type[IEncoder] = {self.ref_name_pretty(FilteringJsonEncoder)}'
            yield
            
            yield from self.write_method_head('__init__', params=[ self.join_attribute('server', Some(server_type), default_server) ], method_type=MethodType.RegularMethod)
            with self.indent():
                if (enum_name.non_empty):
                    yield f'if (isinstance(server, {enum_name.get})):'
                    with self.indent():
                        yield 'server = server.value'
                    yield
                
                code = \
                """
                super().__init__()
                self.server = server
                self.initialize_logger()
                self.logger = RequestLogger(None, self.logger)
                """
                yield from self.deindent(code.strip('\n').splitlines())
            yield
            
            yield '# region Utility Methods'
            yield from self.dump_class_methods(openapi_parser.exporter.exporting_features.client)
            yield '# endregion'
            
            yield '# region Authorization Methods'
            yield from self.dump_client_authorization(parser)
            yield '# endregion'
            
            yield '# region Client Methods'
            for path, mdl in parser.path_items.items():
                for http_method, e in mdl.endpoints.items():
                    yield from self.dump_endpoint(e, endpoint_path=mdl.endpoint_path, http_method=http_method, method_type=MethodType.RegularMethod, asynchronous=True)
            yield '# endregion'
            yield
    
    def dump_client_file(self, parser: OpenApiParser) -> Iterator[str]:
        yield from self.dump_headers()
        yield from self.dump_client_class(parser)
        yield from self.dump_footers()
    
    # region Writers
    @yielder
    def yield_client_class(self, p: OpenApiParser) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_client_class(p)
    
    @overload
    def write_client_class(self, p: OpenApiParser) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_client_class(self, p: OpenApiParser, *, file: StrIO) -> None:
        pass
    @writer
    def write_client_class(self, p: OpenApiParser) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_client_class(p)
    
    @yielder
    def yield_client_file(self, p: OpenApiParser) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_client_file(p)
    
    @overload
    def write_client_file(self, p: OpenApiParser) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_client_file(self, p: OpenApiParser, *, file: StrIO) -> None:
        pass
    @writer
    def write_client_file(self, p: OpenApiParser) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_client_file(p)
    # endregion


__all__ = \
[
    'ClientWriter',
]
