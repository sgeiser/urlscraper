from typing import *

from camel_case_switcher import dict_keys_camel_case_to_underscore
from dataclasses import dataclass, field, InitVar
from tornado.httpserver import HTTPServer
from tornado.httputil import HTTPServerRequest, HTTPMessageDelegate
from tornado.ioloop import IOLoop
from tornado.routing import Rule, RuleRouter, ReversibleRuleRouter, AnyMatches
from tornado.web import _ApplicationRouter as ApplicationRouter

from .discoverable import Discoverable
from .host import Host
from .interfaces import *
from .tools.config_loader import ConfigLoader
from .tools.dataclass_with_settings import dataclass_with_settings
from .tools.logging import ExtendedLogger, get_logger

DEFAULT_ARGUMENT = object()
@dataclass
@dataclass_with_settings(settings_func='initialize_settings')
class ApplicationBase2(IApplication, Discoverable):
    hosts: List[Host] = None
    
    internal_router_class: Type[RuleRouter] = ApplicationRouter
    router: ReversibleRuleRouter = None
    
    listen_port: InitVar[int] = None
    use_default_host: bool = True
    default_host: Host = field(repr=False, default=None)
    default_host_name: InitVar[str] = 'self'
    
    logger_name: str = 'http_server'
    access_logger_name:  str = None
    access_logger: Optional[ExtendedLogger] = field(repr=False, default=None)
    
    hosts_map: Dict[str, Host] = field(init=False, repr=False, default_factory=dict)
    servers: List[HTTPServer] = field(init=False, repr=False, default_factory=list)
    default_server: HTTPServer = field(init=False, repr=False, default=None)
    
    config_priority: InitVar[bool] = False
    config_name: InitVar[str] = 'main'
    config_prefix: InitVar[str] = 'HTTP'
    extra_settings: InitVar[Dict[str, Any]] = None
    
    def __post_init__(self, listen_port: int, default_host_name: str, config_priority: bool, config_name: str, config_prefix: str, extra_settings: Dict[str, Any]):
        self.initialize_logger()
        if (self.access_logger_name is not None and self.access_logger is None):
            self.access_logger = get_logger(self.logger_name)
        
        # Routers
        if (self.router is None):
            self.router = ReversibleRuleRouter()
        
        # Hosts
        if (self.servers is None):
            self.servers = list()
        self.default_server = HTTPServer(self)
        
        if (self.hosts is None):
            _hosts = list()
        else:
            _hosts = list(self.hosts)
        self.hosts = list()
        if (self.use_default_host):
            if (self.default_host is None):
                self.default_host = Host(self, default_host_name, port=listen_port, bind_address='', router_class=self.internal_router_class, matcher=AnyMatches())
            self.add_host(self.default_host)
        for host in _hosts:
            self.add_host(host)
        
        # Handlers
        if (isinstance(self.handlers, dict)):
            for host, handlers in self.handlers.items():
                self.add_handlers(handlers, host)
        else:
            self.add_handlers(self.handlers)
        for controller in self.handler_controllers:
            self.attach_handler_controller(controller)
        
        # Other
        _def_host = self.default_host
        super(IApplication, self).__init__(**self.settings)
        self.default_host = _def_host
        if (self.use_default_host and self.wildcard_router):
            self.add_handlers(self.wildcard_router.rules)
        self.servers.append(self.default_server)
    
    def initialize_settings(self, *args, config_priority: bool, config_name: str, config_prefix: str, extra_settings: Dict[str, Any], **kwargs):
        if (extra_settings is None):
            extra_settings = dict()
        extra_settings.update(kwargs)
        self.settings: Dict[str, Any] = dict_keys_camel_case_to_underscore(ConfigLoader.get_from_config(config_prefix, config_name, default=dict()), recursive=True)
        self.settings.update(extra_settings)
        if ('port' in self.settings):
            self.settings['listen_port'] = self.settings.pop('port')
        
        _s = dict()
        priorities: List[Dict[str, Any]] = [ self.__dict__, self.settings ]
        if (config_priority):
            priorities = list(reversed(priorities))
        for p in priorities:
            _s.update(p)
        return _s
    
    #region Hosts, Handlers and Requests
    def add_host(self, host: Union[Host, str, dict]):
        if (isinstance(host, Host)):
            host.application = self
            host.router.application = self
        elif (isinstance(host, str)):
            host = Host(self, host, router_class=self.internal_router_class)
        elif (isinstance(host, tuple)):
            host = Host(self, *host, router_class=self.internal_router_class)
        elif (isinstance(host, dict)):
            host.setdefault('router_class', self.internal_router_class)
            host = Host(self, **host)
        else:
            raise ValueError(f"Invalid host argument: '{host}' (type: {type(host)})")
        
        if (host.ssl_options is not None):
            server = HTTPServer(self, ssl_options=host.ssl_options)
            self.servers.append(server)
        else:
            server = self.default_server
        host.attached_http_server = server
        
        self.logger.info(f"Adding host '{host.name}': {host}")
        self.router.rules.insert(0, host.rule)
        self.hosts.append(host)
        self.hosts_map[host.name] = host
    
    def find_handler(self, request: HTTPServerRequest, **kwargs) -> Optional[HTTPMessageDelegate]:
        request = self.normalize_request(request)
        return self.router.find_handler(request, **kwargs)
    
    def add_handlers(self, handlers: List[Union[Rule, HandlerType]], host: str = None, respect_default_host: bool = True):
        added = False
        if (host is not None):
            if (host not in self.hosts_map):
                raise ValueError(f"Host '{host}' is not registered")
            self.hosts_map[host].router.add_rules(handlers)
            added = True
        if (self.use_default_host and respect_default_host):
            self.default_host.router.add_rules(handlers)
            added = True
        
        if (not added):
            self.logger.warning("No handlers were added by add_handlers() due to the invalid configuration (neither host nor default router were configured)")
    
    def attach_handler_controller(self, controller: IHandlerController):
        for host in self.hosts:
            self.add_handlers(controller.get_handlers_for(host.name), host.name, respect_default_host=False)
    
    def normalize_request(self, request: HTTPServerRequest) -> HTTPServerRequest:
        path, sep, query = request.uri.partition('?') # type: str, str, str
        _new_path = '/'.join([''] + [_part for _part in path.split('/') if _part])
        if (path.endswith('/')):
            _new_path += '/'
        if (_new_path != path):
            _new_uri = _new_path + sep + query
            self.logger.trace(f"Rewriting uri: '{path}' => '{_new_path}'")
            request.uri = _new_uri
            request.path = _new_path
        return request
    #endregion
    
    #region Start server
    def start_listening(self):
        _listened = set()
        for host in self.hosts:
            _name = host.name
            if (host is self.default_host):
                _name += ' (default)'
            
            _repr = f"{_name} host: {host.address} (bind address='{host.bind_address}', port={host.port})"
            if ((host.port, host.bind_address) in _listened):
                self.logger.info(f"{self.name}: Reusing listening socket for the {_repr} has already been bound")
                continue
            
            self.logger.info(f"{self.name}: Listening on the {_repr}")
            host.attached_http_server.listen(host.port, host.bind_address)
            _listened.add((host.port, host.bind_address))
    
    def run(self, blocking=True, num_processes=1):
        """
        Runs the server on the port specified earlier.
        Server blocks the IO.
        """
        
        self.logger.info(f"{self.name}: Starting HTTP service...")
        self.start_listening()
        self.default_server.start(num_processes=num_processes)
        self.logger.info(f"{self.name}: Service started")
        
        if (blocking):
            IOLoop.current().start()
    
    @classmethod
    def simple_start_prepare(cls):
        from .tools.logging import setup_logging
        
        # Configure logger
        setup_logging()
        logger = get_logger(cls.logger_name)
        logger.setLevel('TRACE')
        logger.info("Logger started")
        ConfigLoader.load_configs(soft_mode=True)
        
        return logger
    
    @classmethod
    def _simple_start_func(cls, pre_run_func: Union[Callable[['ApplicationBase2'], None], None], num_processes=1, blocking=True, **settings) -> Tuple[Union['ApplicationBase2', None], Union[Exception, None]]:
        """
        If any expected error occurs, returns the instance of initialized class (if any) and the exception
        
        :param pre_run_func:
        Function to be run after the server initialization but before actual start.
        Must take only one argument - the server instance.
        :param settings:
        Settings used for the server initialization
        :return:
        Tuple:
         - instance of initialized object (if any)
         - exception info
        """
        
        server_application: ApplicationBase2 = cls(**settings)
        if (callable(pre_run_func)):
            pre_run_func(server_application)
        
        try:
            server_application.run(num_processes=num_processes, blocking=blocking)
        except KeyboardInterrupt:
            server_application.logger.info("Keyboard interrupt. Exiting now.")
        except PermissionError as e:
            return server_application, e
        
        return None, None
    
    @classmethod
    def simple_start_server(cls, pre_run_func: Union[Callable[['ApplicationBase2'], None], None] = None, **settings):
        """
        Initializes logging and ConfigLoader in the soft-mode,
        than initializes the class instance, runs this function and starts the server.
        
        :param pre_run_func:
        Function to be run after the server initialization but before actual start.
        Must take only one argument - the server instance.
        :param settings:
        Settings used for the server initialization
        :return:
        """
        
        logger = cls.simple_start_prepare()
        
        try:
            server_application, exception = cls._simple_start_func(pre_run_func, **settings)
            
            if (isinstance(exception, PermissionError)):
                server_application.logger.error("Permission error. Restarting server with the port of range 8xxx.")
                new_port = server_application.default_host.port + 8000
                del server_application
                settings['listen_port'] = new_port
                logger.info(f"Restarting server on the port {new_port}.")
                cls._simple_start_func(pre_run_func, **settings)
        
        except Exception:
            logger.exception(msg="Unhandled exception while starting server:")
            raise
    #endregion

__all__ = \
[
    'ApplicationBase2',
]
