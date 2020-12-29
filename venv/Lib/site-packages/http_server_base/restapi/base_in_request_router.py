import inspect
import re
from functools import wraps
from typing import *

import parse
from typing.re import *

from http_server_base.logged_request_handler import Logged_RequestHandler
from http_server_base.model import IEncoder
from http_server_base.tools.logging import get_logger
from .interfaces import *
from .interfaces import DEFAULT_ALLOWED_METHODS

logger = get_logger('http_server_base.restapi.helper')

TKey = TypeVar('TKey')
TMapper = TypeVar('TMapper')
class BaseInRequestRouter(IInRequestRouter[TMapper, TKey]):
    _TEndpointMapper = MutableMapping[str, Endpoint[TKey]]
    _TInClassMapper = Dict[str, _TEndpointMapper]
    _TGlobalMapper = Dict[str, _TInClassMapper]
    
    # Dictionary: class_full_name (with module) -> method_lower -> path -> rest_method scope dict
    method_mapper: _TGlobalMapper = dict()
    
    @classmethod
    def get_class_name(cls, tp: type) -> str:
        _name = getattr(tp, 'class_name', None)
        if (_name is not None):
             return _name
        
        _m = inspect.getmodule(tp)
        _class_name = tp.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        return f'{_m.__name__}.{_class_name}'
    
    @classmethod
    def get_function_parent_class(cls, func) -> Optional[type]:
        if (inspect.ismethod(func)):
            for _cls in inspect.getmro(func.__self__.__class__):
                if (_cls.__dict__.get(func.__name__) is func):
                    return _cls
            func = func.__func__  # fallback to __qualname__ parsing
        
        if (inspect.isfunction(func)):
            _m = inspect.getmodule(func)
            _class_name = func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
            return getattr(_m, _class_name)
        
        return None  # not required since None would have been implicitly returned anyway
    
    @classmethod
    def get_function_parent_class_name(cls, func) -> Optional[str]:
        if (inspect.ismethod(func)):
            for _cls in inspect.getmro(func.__self__.__class__):
                if (_cls.__dict__.get(func.__name__) is func):
                    return cls.get_class_name(_cls)
            func = func.__func__  # fallback to __qualname__ parsing
        
        if (inspect.isfunction(func)):
            _m = inspect.getmodule(func)
            _class_name = func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
            return f'{_m.__name__}.{_class_name}'
        
        return None  # not required since None would have been implicitly returned anyway
    
    @classmethod
    def convert_to_tuple(cls, x) -> Tuple:
        if (isinstance(x, tuple)):
            return x
        return (x, )
    
    PARAMETER_PATTERNS = \
    {
        str: r'\w\s-]+',
        int: r'[0-9]+',
        float: r'[0-9]+(\.[0-9]*)?',
        bool: r'true|false',
        None: r'[^/?#]+',
    }
    
    @classmethod
    def get_class_mapper(cls,x: Union[Type[IRest_RequestHandler], str]) -> _TInClassMapper:
        class_name = None
        if (isinstance(x, type)):
            class_name = cls.get_class_name(x)
        elif (isinstance(x, str)):
            class_name = x
        
        class_dict = cls.method_mapper.get(class_name) or cls.mapper_type()
        return class_dict
    
    @classmethod
    def get_class_endpoints(cls, x: Union[Type[IRest_RequestHandler], str]) -> Iterator[Tuple[str, str]]:
        """
        Returns an iterator over (HTTP Method, Path) pairs for class endpoints
        
        :param x: str, : target class
        :return: Iterator[str, str]
        """
        
        mapper = cls.get_class_mapper(x)
        for http_method in mapper:
            for ctx in mapper[http_method].values():
                yield http_method, ctx.path
    
    @classmethod
    def remove_base_path(cls, path: str, base_path: str) -> str:
        sep = '/'
        path = sep + sep.join(x for x in path.split(sep) if x)
        
        if (path.startswith(base_path)):
            path = path[len(base_path):]
            if (not path.startswith(sep)):
                path = sep + path
        
        return path
    
    @classmethod
    def get_mapper_func(cls, x: Union[Type[IRest_RequestHandler], str]) -> MapperFuncType:
        class_dict = cls.get_class_mapper(x)
        def func(method: str, path: str, base_path: str = '') -> Tuple[str, Callable]:
            method = method.lower()
            if (not method in class_dict):
                raise MethodNotAllowedError(f"Method {method.upper()} is not allowed")
            
            path = cls.remove_base_path(path, base_path)
            _func = class_dict[method][path].action
            return path, _func
        return func
    
    @classmethod
    def get_canonical_form_of_argument(cls, arg: ArgumentType) -> CanonicalArgumentType:
        """
        Extracts the argument info from the free argument description form
        :param arg:
        Either str or tuple
        Str: argument_name. Any type. No default. Mandatory
        
        Tuple:
            (argument_name): the same
            (argument_name, argument_type): No default. Mandatory.
            (argument_name, argument_types, argument_default): Optional.
        
        Where:
            argument_name: str. Can have leading '?', marking argument as an optional (None will be returned if no default). Can have '=', making everything behind it the argument_default.
            argument_types: Type or Tuple of Types. Types used for strict type checks. 'None' is any type.
            argument_default: any legal type. The default value is returned if the argument itself is missing.
        :return:
        
        Tuple:
            (argument_name: str, argument_types: Tuple[Type+], argument_default, mandatory: bool)
        
        Where:
            mandatory: True if argument is mandatory, False if optional.
        """
        
        arg = cls.convert_to_tuple(arg)
        required: bool = True
        param_name: str = arg[0]
        param_types: Union[Tuple[Optional[Type], ...], Set[Any]]
        if (len(arg) > 1):
            param_types = cls.convert_to_tuple(arg[1])
            if (any(not isinstance(_arg, type) and not _arg is None for _arg in list(param_types))):
                if (len(param_types) == 1):
                    param_types = set(list(param_types)[0])
                else:
                    param_types = set(param_types)
        else:
            param_types = (None,)
        
        if (len(arg) > 2):
            param_default = arg[2]
            required = False
        elif ('=' in param_name):
            param_name, _, param_default = param_name.partition('=')
            required = False
        else:
            param_default = cls.DEFAULT_ARG
        
        if (param_name.startswith('?')):
            param_name = param_name[1:]
            if (None not in param_types):
                param_types = param_types + (None, )
            required = False
        
        return param_name, param_types, param_default, required
    @classmethod
    def get_canonical_form_of_argument_list(cls, args: ArgumentListType) -> CanonicalArgumentListType:
        if (args is None):
            return list()
        
        return [ cls.get_canonical_form_of_argument(arg) for arg in args]
    
    @classmethod
    def patternize(cls, uri: str, url_args: ArgumentListType = IInRequestRouter.DEFAULT_ARG) -> Tuple[str, List[str]]:
        result = re.escape(uri)
        
        if (url_args is None):
            keys = list()
        
        elif (url_args is cls.DEFAULT_ARG):
            result = result.replace('\\{', '{').replace('\\}', '}')
            parameters = parse.parse(result, result).named
            for _param_name in parameters:
                _pattern = cls.PARAMETER_PATTERNS[None]
                _pattern = rf'(?P<{_param_name}>{_pattern})'
                result = result.replace(parameters[_param_name], _pattern)
            keys = parameters.keys()
        
        else:
            keys = list()
            for _arg in url_args:
                _pattern = cls.PARAMETER_PATTERNS[None]
                
                _arg = cls.convert_to_tuple(_arg)
                _param_name = _arg[0]
                if (len(_arg) > 1):
                    if (isinstance(_arg[1], set)):
                        _pattern = rf"({r')|('.join(re.escape(str(_x)) for _x in _arg[1])})"
                    
                    else:
                        _param_types = cls.convert_to_tuple(_arg[1])
                        _patterns = list()
                        for _param_type in _param_types:
                            _p = cls.PARAMETER_PATTERNS.get(_param_type, cls.DEFAULT_ARG)
                            if (not _p is cls.DEFAULT_ARG):
                                _patterns.append(_p)
                        
                        if (len(_patterns) > 0):
                            _pattern = rf"({r')|('.join(_patterns)})"
                
                result = result.replace(f'\\{{{_param_name}\\}}', rf"(?P<{_param_name}>{_pattern})")
                keys.append(_param_name)
        
        return r'^' + result + r'/?(\?.+)?$', keys
    
    @classmethod
    def get_path_regular(cls, path: str,  path_args: ArgumentListType = IInRequestRouter.DEFAULT_ARG, **kwargs) -> Tuple[Pattern[str], ArgumentListType]:
        if (path is not None):
            _regular_s, _url_params = cls.patternize(path, path_args)
            if (path_args == cls.DEFAULT_ARG):
                path_args = _url_params
            _regular = re.compile(_regular_s, flags=re.IGNORECASE)
        else:
            raise ValueError("Path must be presented")
        
        return _regular, path_args
    
    @classmethod
    def get_path_key(cls, *, path: str, **kwargs) -> str:
        sep = '/'
        return sep + sep.join(x for x in path.lower().split(sep) if x)
    
    T = TypeVar('T')
    @classmethod
    def encode_result \
    (
        cls,
        encoder: Union[IEncoder[T], Type[IEncoder[T]]],
        model: Type[T],
    ):
        """
        Decorates method that returns instance of T
        to return json-encoded (via dicts and lists) value
        via the IEncoder[T].
        
        :param encoder: IEncoder[T] or Type[IEncoder[T]]
        :param model: Type[T]
        :return: decorated async method
        """
        if (encoder is None or not (isinstance(encoder, IEncoder) or isinstance(encoder, type) and issubclass(encoder, IEncoder))):
            raise ValueError(f"Invalid encoder specified, expected: IEncoder, got: '{encoder}' (type: '{type(encoder).__name__}')")
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if (inspect.isawaitable(result)):
                    result = await result
                result = encoder.encode_smart(model, result)
                return result
            return wrapper
        return decorator
    
    @classmethod
    def simple_return(cls, *f):
        """
        Decorates a Logged_RequestHandler method
        to call resp_success on a method result.
        
        :param f: Function to decorate, or missing
        :return: Either a decorator to or a decorated async function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(self: Logged_RequestHandler, *args, **kwargs):
                result = func(self, *args, **kwargs)
                if (inspect.isawaitable(result)):
                    result = await result
                self.resp_success(result=result)
                return result
            return wrapper
        
        if (f):
            return decorator(*f)
        else:
            return decorator
    
    @classmethod
    def rest_method \
    (
        cls,
        path: str = '/',
        method: Union[str, List[str], Tuple[str]]='GET',
        *,
        path_args: ArgumentListType = IInRequestRouter.DEFAULT_ARG,
        body_args: ArgumentListType = None,
        query_args: ArgumentListType = None,
        header_args: ArgumentListType = None,
        support_arguments_capitalization_style_switch: bool = False,
        simple_return: bool = False,
        
        class_name: str = None,
        return_method_info: bool  =  False,
        **kwargs,
    ):
        if (method == '*'):
            method = DEFAULT_ALLOWED_METHODS
        
        key = cls.get_path_key(path=path, **kwargs)
        _regular, path_args = cls.get_path_regular(path=path, path_args=path_args, **kwargs)
        logger.debug(f"Rest method registrator generator is called for the method {str(method).upper()}: {key}")
        
        path_args = cls.get_canonical_form_of_argument_list(path_args)
        body_args = cls.get_canonical_form_of_argument_list(body_args)
        query_args = cls.get_canonical_form_of_argument_list(query_args)
        header_args = cls.get_canonical_form_of_argument_list(header_args)
        
        # This will NOT decorate a function
        # It only registers it
        def rest_method__registrator(func, http_method=None):
            if (http_method is None):
                http_method = method
            if (isinstance(http_method, (list, tuple))):
                _results = list()
                for _method in http_method:
                    _method = _method.lower()
                    _results.append(rest_method__registrator(func, http_method=_method))
                if (return_method_info):
                    return _results
                else:
                    return func
            elif (isinstance(http_method, str)):
                _method = http_method.lower()
            else:
                raise TypeError(f"http_method must be either str, List[str] or Tuple[str], not {type(http_method)}")
            
            _class_name = class_name or cls.get_function_parent_class_name(func)
            logger.debug(f"Rest registrator is called on the '{_class_name}' / {func.__name__}")
            
            async def rest_method__registrator__action(self: IRest_RequestHandler, url, *parsed_path_args, **parsed_path_kwargs):
                
                _path_match = _regular.match(url)
                unparsed_path_args = _path_match.groupdict() if (_path_match) else dict()
                
                try:
                    path_kwargs   = self.get_args(unparsed_path_args,           path_args,   source_type='path',    support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                    body_kwargs   = self.get_args(self.request.body_arguments,  body_args,   source_type='body',    support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                    query_kwargs  = self.get_args(self.request.query_arguments, query_args,  source_type='query',   support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                    header_kwargs = self.get_args(self.request.headers,         header_args, source_type='headers', support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                except ArgumentError:
                    return
                
                result = func(self, **path_kwargs, **body_kwargs, **query_kwargs, **header_kwargs)
                if (inspect.isawaitable(result)):
                    result = await result
                return result
            
            if (simple_return):
                rest_method__registrator__action = cls.simple_return(rest_method__registrator__action)
            if (not _class_name in cls.method_mapper):
                cls.method_mapper[_class_name] = dict()
            if (not _method in cls.method_mapper[_class_name]):
                cls.method_mapper[_class_name][_method] = cls.mapper_type()
            
            e = Endpoint \
            (
                name = f'{_method.upper()} {path}',
                method = _method,
                key = key,
                path = path,
                paths = (path, key),
                query_arguments = query_args,
                body_arguments = body_args,
                path_arguments = path_args,
                header_arguments = header_args,
                action = rest_method__registrator__action,
                extra_args = locals(),
                matches = lambda p: False,
            )
            e.matches = lambda p: cls.method_mapper[_class_name][_method].get(p) is e
            cls.method_mapper[_class_name][_method][key] = e
            
            if (return_method_info):
                return cls.method_mapper[_class_name][_method][key]
            else:
                return func
        
        return rest_method__registrator
    
    @classmethod
    def extract_args \
    (
        cls,
        *,
        body_args: ArgumentListType = None,
        query_args: ArgumentListType = None,
        header_args: ArgumentListType = None,
        support_arguments_capitalization_style_switch: bool = False,
        
        class_name: str = None,
        **kwargs
    ):
        
        body_args = cls.get_canonical_form_of_argument_list(body_args)
        query_args = cls.get_canonical_form_of_argument_list(query_args)
        header_args = cls.get_canonical_form_of_argument_list(header_args)
        
        def extract_args__decorator(func):
            _class_name = class_name or cls.get_function_parent_class_name(func)
            logger.debug(f"Rest argument extractor generator is called on the {_class_name} / {func.__name__}")
            
            @wraps(func)
            def extract_args__decorator__wrapper(self, *args, **kwargs):
                try:
                    body_kwargs   = self.get_args(self.request.body_arguments, body_args,     source_type='body',    support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                    query_kwargs  = self.get_args(self.request.query_arguments, query_args,   source_type='query',   support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                    header_kwargs = self.get_args(self.request.headers, header_args,          source_type='headers', support_capitalization_style_switch=support_arguments_capitalization_style_switch)
                except ArgumentError:
                    return
                
                result = func(self, *args, **kwargs, **body_kwargs, **query_kwargs, **header_kwargs)
                return result
            return extract_args__decorator__wrapper
        return extract_args__decorator

__all__ = \
[
    'BaseInRequestRouter',
]
