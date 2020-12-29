import json
from typing import *

from tornado.httpclient import HTTPResponse, HTTPRequest as HTTPClientRequest
from tornado.httputil import HTTPServerRequest

from .interfaces import *
from .tools.extensions import server_request_to_client_request
from .tools.types import JsonSerializable

def get_response(handler: ILogged_RequestHandler, func: Callable, code: int, reason: str = None, request: Union[HTTPClientRequest, HTTPServerRequest, None] = None, *args, **kwargs):
    if (request is None):
        request = handler.request
    if (isinstance(request, HTTPServerRequest)):
        request = server_request_to_client_request(handler.request)
    
    response_instance = HTTPResponse(request=request, code=code, reason=reason)
    _r = func(handler, response_instance, *args, **kwargs)
    if (_r is not None):
        response_instance = _r
    if (response_instance.buffer is None):
        response_instance.buffer = True
        if (response_instance._body is None):
            response_instance._body = b''
    return response_instance

def error_decorator(func: Callable) -> Tuple[Callable, Callable]:
    def get_error_response(handler: ILogged_RequestHandler, code=500, *args, **kwargs) -> HTTPResponse:
        return get_response(handler, func, code, *args, **kwargs)    
    def resp_error(handler: ILogged_RequestHandler, code=500, reason=None, message=None, *args, **kwargs):
        handler.logger.info('{0}' if reason else '{0}: {1}', code, reason, prefix='resp')
        if (message is not None):
            handler.logger.warning('{}', message, prefix='resp')
        
        response_instance = get_error_response(handler, code, reason, message=message, *args, **kwargs)
        handler.set_response(response_instance, clear=True)
        handler.finish()
    
    return get_error_response, resp_error

def success_decorator(func):
    def get_success_response(handler: ILogged_RequestHandler, code=200, *args, **kwargs) -> HTTPResponse:
        return get_response(handler, func, code, *args, **kwargs)    
    
    def resp_success(handler: ILogged_RequestHandler, code=200, reason=None, message=None, result=None, *args, **kwargs):
        if (handler._finished):
            raise RuntimeWarning("Ignoring response as the request has already been sent")
        
        handler.logger.info('{0}' if reason else '{0}: {1}', code, reason, prefix='resp')
        if (message is not None):
            handler.logger.debug('{}', message, prefix='resp')
        if (result is not None):
            handler.logger.debug('{}', result, prefix='resp')
        
        response_instance = get_success_response(handler, code, reason, message=message, result=result, *args, **kwargs)
        handler.set_response(response_instance, clear=False)
    
    return get_success_response, resp_success

def apply_decorators(cls: Type[IResponder]) -> Type[IResponder]:
    if (isinstance(cls.update_error_response, tuple)):
        cls.get_error_response, cls.resp_error = cls.update_error_response
    if (isinstance(cls.update_success_response, tuple)):
        cls.get_success_response, cls.resp_success = cls.update_success_response
    return cls

@apply_decorators
class BasicResponder(IResponder):
    """
    Works ONLY for the ILogged_RequestHandler
    """
    @staticmethod
    @error_decorator
    def update_error_response(handler: ILogged_RequestHandler, response: HTTPResponse, message):
        pass
    @staticmethod
    @success_decorator
    def update_success_response(handler: ILogged_RequestHandler, response: HTTPResponse, message, result):
        pass

@apply_decorators
class TextBasicResponder(BasicResponder):
    @staticmethod
    @error_decorator
    def update_error_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None):
        pass
    
    @staticmethod
    @success_decorator
    def update_success_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None, result=None):
        if (result):
            response.headers.add('Content-Type', 'text/plain')
            response._body = bytes(str(result), 'utf8')

@apply_decorators
class HtmlBasicResponder(BasicResponder):
    @staticmethod
    @error_decorator
    def update_error_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None):
        code = response.code
        reason = response.reason
        response.headers.add('Content-Type', 'text/html')
        _html = f'<html><title>{code}: {reason}</title><body>{message}</body></html>'
        response._body = bytes(_html, 'utf8')
    
    @staticmethod
    @success_decorator
    def update_success_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None, result=None):
        code = response.code
        reason = response.reason
        if (not result is None):
            response.headers.add('Content-Type', 'text/html')
            _html = f'<html><title>{code}: {reason}</title><body>{message}:<br/>{str(result)}</body></html>'
            response._body = bytes(_html, 'utf8')

@apply_decorators
class JsonCustomResponder(BasicResponder):
    def _make_response(handler: ILogged_RequestHandler, response_instance: HTTPResponse, *args, response: JsonSerializable = None, **kwargs):
        _resp_str = json.dumps(response, sort_keys=True)
        handler.logger.debug(_resp_str, prefix='resp')
        response_instance.headers.add('Content-Type', 'application/json')
        response_instance._body = bytes(_resp_str, 'utf8')
    
    update_error_response = error_decorator(_make_response)
    update_success_response = success_decorator(_make_response)

@apply_decorators
class JsonBasicResponder(BasicResponder):
    @staticmethod
    @error_decorator
    def update_error_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None, **kwargs):
        response.headers.add('Content-Type', 'application/json')
        _json = dict(success=False, code=response.code, reason=response.reason, **kwargs)
        if (message is not None):
            _json['message'] = message
        response._body = bytes(json.dumps(_json), 'utf8')
    
    @staticmethod
    @success_decorator
    def update_success_response(handler: ILogged_RequestHandler, response: HTTPResponse, message=None, result=None, **kwargs):
        response.headers.add('Content-Type', 'application/json')
        _json = dict(success=True, code=response.code, reason=response.reason, **kwargs)
        if (message is not None):
            _json['message'] = message
        if (result is not None):
            _json['result'] = result
        response._body = bytes(json.dumps(_json), 'utf8')

__all__ = \
[
    # Functions
    'error_decorator',
    'success_decorator',
    'apply_decorators',
    
    # Classes
    'BasicResponder',
    'HtmlBasicResponder',
    'JsonBasicResponder',
    'JsonCustomResponder',
    'TextBasicResponder',
]
