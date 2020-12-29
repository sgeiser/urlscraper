from abc import ABC
from io import BytesIO
from socket import gaierror as DNSNameNotResolvedError
from typing import *

from tornado.httpclient import HTTPRequest as HTTPClientRequest, HTTPResponse
from tornado.httputil import HTTPServerRequest
from tornado.simple_httpclient import HTTPTimeoutError

from .interfaces import ILoggable
from .tools.extensions import server_request_to_client_request

ErrorMatcherFunction = Callable[[Union[HTTPClientRequest, HTTPServerRequest], Exception], HTTPResponse]

class CanonicalErrorResponseDescriptor:
    code: int
    message: str
    func: ErrorMatcherFunction
    
    def __init__(self, code: int = None, message: str = None, func: ErrorMatcherFunction = None):
        self.code = code
        self.message = message
        self.func = func

ErrorResponseDescriptor = Union \
[
    int,
    Tuple[int],
    Tuple[int, str],
    Dict[str, Union[str, int]],
    CanonicalErrorResponseDescriptor,
]

class ErrorMatcher(ILoggable, ABC):
    
    DEFAULT_ERROR_DESCRIPTOR = 500
    DEFAULT_ERRORS_MAPPER = \
    [
        (DNSNameNotResolvedError, 502),
        (ConnectionError, 502),
        (HTTPTimeoutError, 504),
        (TimeoutError, 504),
        (Exception, DEFAULT_ERROR_DESCRIPTOR),
    ]
    error_map: List[Tuple[Type[Exception], ErrorResponseDescriptor]] = list(DEFAULT_ERRORS_MAPPER)
    
    def _parse_error_response_descriptor(self, error_type, value) -> CanonicalErrorResponseDescriptor:
        if (isinstance(value, int)):
            value = CanonicalErrorResponseDescriptor(value)
        elif (isinstance(value, tuple)):
            value = CanonicalErrorResponseDescriptor(*value)
        elif (isinstance(value, dict)):
            value = CanonicalErrorResponseDescriptor(**value)
        else:
            raise ValueError(f"Unsupported argument type: '{type(value)}' (index: '{error_type}'), expected: int, tuple, dict")
        
        return value   
    
    def match_error(self, request: Union[HTTPClientRequest, HTTPServerRequest], error: Exception) -> HTTPResponse:
        
        matcher_func = None
        for error_type, descriptor in self.error_map:
            if (isinstance(error, error_type)):
                matcher_func = self.get_error_matcher_func(error_type, descriptor)
                break
        
        if (matcher_func is None):
            matcher_func = self.get_error_matcher_func("Default error", self.DEFAULT_ERROR_DESCRIPTOR)
        
        response = matcher_func(request, error)
        self.logger.exception(f"Handling exception: {type(error)} => {response.code} {response.request} {response.body.decode()}")
        return response
    
    def get_error_matcher_func(self, key, descriptor: ErrorResponseDescriptor) -> ErrorMatcherFunction:
        descriptor = self._parse_error_response_descriptor(key, descriptor)
        if (descriptor.func is not None):
            return descriptor.func
        else:
            return lambda req, exc: self._default_error_matcher(req, exc, descriptor)
    
    def _default_error_matcher(self, request: Union[HTTPClientRequest, HTTPServerRequest], exception: Exception, descriptor: CanonicalErrorResponseDescriptor) -> HTTPResponse:
        message = descriptor.message or f"{exception}"
        code = descriptor.code or 500
        if (isinstance(request, HTTPServerRequest)):
            request = server_request_to_client_request(request)
        return self._default_error_matcher__create_response(request=request, code=code, message=message, error=exception)
    def _default_error_matcher__create_response(self, request: HTTPClientRequest, code: int, message: str, **kwargs) -> HTTPResponse:
        response = HTTPResponse(request, code, buffer=BytesIO(message.encode()), **kwargs)
        return response

__all__ = \
[
    'ErrorResponseDescriptor',
    'ErrorMatcherFunction',
    'CanonicalErrorResponseDescriptor',
    'ErrorMatcher',
]
__pdoc_extras__ = \
[
    'ErrorResponseDescriptor',
    'ErrorMatcherFunction',
]
