import re
import socket
from ssl import create_default_context, Purpose, SSLContext
from typing import *

from dataclasses import dataclass, field, InitVar
from tornado.httpserver import HTTPServer
from tornado.routing import HostMatches, Rule, RuleRouter, Matcher
from tornado.web import _ApplicationRouter as ApplicationRouter
from typing.re import *

from .interfaces import *
from .strict_host_matches import StrictHostMatches
from .tools.dataclass_with_settings import dataclass_with_settings

@dataclass
@dataclass_with_settings
class Host(ILoggable):
    application: IApplication = field(repr=False)
    name: str
    protocol: str = None
    port: int = None
    address: str = None
    bind_address: str = ''
    
    pattern: Union[str, Pattern[str]] = None
    matcher: Matcher = None
    router_class: Type[RuleRouter] = ApplicationRouter
    router: RuleRouter = field(default=None, repr=False)
    rule: Rule = field(default=None, repr=False)
    
    attached_http_server: HTTPServer = field(init=False, repr=False, default=None)
    ssl_options: Union[Dict[str, Any], SSLContext, None] = None
    ssl_enabled: bool = None
    ssl_certificate_path: InitVar[str] = None
    ssl_private_key_path: InitVar[str] = None
    
    logger_name: str = None
    settings: Dict[str, Any] = field(init=False, repr=False)
    
    def __post_init__(self, ssl_certificate_path, ssl_private_key_path):
        if (self.logger_name is None):
            self.logger_name = f'{self.application.logger_name}.{self.name}'
        self.initialize_logger()
        
        self.settings = self._get_settings()
        self.ssl_options = self._get_ssl(ssl_certificate_path, ssl_private_key_path)
        
        if (self.protocol is None):
            self.protocol = 'https' if (self.ssl_enabled) else 'http'
        if (self.port is None):
            self.port = 443 if (self.ssl_enabled) else 80
        if (self.address is None):
            self.address = self._get_address()
        if (self.pattern is None):
            self.pattern = re.escape(self.bind_address)
        if (self.matcher is None):
            self.matcher = HostMatches(self.pattern) if (self.pattern) else StrictHostMatches(protocol=self.protocol, port=self.port)
        if (self.router is None):
            params = dict()
            if (issubclass(self.router_class, IRouter)):
                params['owner'] = self
            # noinspection PyArgumentList
            self.router = self.router_class(self.application, **params)
        if (self.rule is None):
            self.rule = Rule(self.matcher, target=self.router, name=f"Host:{self.name}")
    
    def _get_settings(self, *args, **kwargs):
        self.settings = dict(self.__dict__)
        self.settings.update(**kwargs)
        if (self.application is not None):
            self.settings.update(self.application.settings)
            if (self.name in self.application.settings):
                self.settings.update(self.application.settings[self.name])
        
        _listen_port = self.settings.pop('listen_port', None)
        if (_listen_port is not None):
            self.settings['port'] = _listen_port
        return self.settings
    
    def _get_ssl(self, ssl_certificate_path, ssl_private_key_path):
        if (self.ssl_options is None):
            self.ssl_options = self.settings.get('ssl_options') or self.settings.get('ssl')
        if (isinstance(self.ssl_options, dict)):
            self.ssl_enabled = self.ssl_options.pop('enabled', None)
            ssl_certificate_path = self.ssl_options.pop('certificate_path', None)
            ssl_private_key_path = self.ssl_options.pop('private_key_path', None)
            if (not self.ssl_options):
                self.ssl_options = None
        
        if (self.ssl_options is None):
            if (self.ssl_enabled is None):
                self.ssl_enabled = self.settings.get('ssl_enabled', False)
            if (self.ssl_enabled):
                if (ssl_certificate_path is None):
                    ssl_certificate_path = self.settings.get('ssl_certificate_path', 'configs/public-cert.crt')
                if (ssl_private_key_path is None):
                    ssl_private_key_path = self.settings.get('ssl_private_key_path', 'configs/private-key.key')
                self.ssl_options = create_default_context(Purpose.CLIENT_AUTH)
                self.ssl_options.load_cert_chain(ssl_certificate_path, ssl_private_key_path)
        else:
            raise ValueError(f"SSL config must be either dict, or None, not '{type(self.ssl_options)}'")
        return self.ssl_options
    
    def _get_address(self) -> str:
        address = self.settings.get(f'{self.name}_address')
        if (address is None):
            get_host_func = getattr(self.application, f'get_{self.name}_host', None)
            if (get_host_func is not None and callable(get_host_func)):
                _host = get_host_func()
                if (isinstance(_host, tuple) and len(_host) == 2):
                    listen_address, host_pattern = _host
                else:
                    listen_address = _host
            else:
                listen_address = \
                    self.settings.get('listen_address') \
                    or self.settings.get('listen_ip') \
                    or self.settings.get('ip') \
                    or socket.gethostbyname(socket.gethostname()) \
            
            address = f"{self.protocol}://{listen_address}:{self.port}"
        return address

__all__ = \
[
    'Host',
]
