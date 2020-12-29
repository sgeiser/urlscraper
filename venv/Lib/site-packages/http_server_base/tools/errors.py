import json
from enum import IntEnum, auto
from typing import *

from tornado.web import HTTPError

from .subrequest_classes import HttpSubrequestResponse
from .types import JsonSerializable

class ServerError(HTTPError):
    resp_error_params: Dict[str, JsonSerializable]
    message: str
    error: str
    code: int
    reason: str
    
    _PARAMS = ('code', 'reason', 'error', 'message')
    _RE_PARAMS = _PARAMS
    def __init__(self, code: int = None, reason: str = None, error: str = None, message: str = None, **kwargs):
        if (code is None):
            code = 500
        
        _locals = locals()
        self.resp_error_params = dict()
        for _var in self._RE_PARAMS:
            _value = _locals[_var]
            if (_value is not None):
                self.resp_error_params[_var] = _value
            setattr(self, _var, _value)
        
        super().__init__(status_code=code, log_message=message)
    
    def reword(self, **kwargs):
        for p in self._PARAMS:
            kwargs.setdefault(p, getattr(self, p))
        
        new_err = type(self)(**kwargs)
        self.args = new_err.args
        return self

class SubrequestFailedErrorCodes(IntEnum):
    StatusCodeMismatch = auto()
    MimeTypeMismatch = auto()
    InvalidResponseBody = auto()
    Other = -1

class SubrequestFailedError(ServerError):
    response: HttpSubrequestResponse
    error_code: SubrequestFailedErrorCodes
    
    _PARAMS = (*ServerError._PARAMS, 'response', 'error_code')
    def __init__ \
    (
        self,
        response: HttpSubrequestResponse,
        *,
        expected_codes: Collection[int] = None,
        expected_mime_type: str = None,
        error_code: SubrequestFailedErrorCodes = None,
        **kwargs,
    ):
        
        error = kwargs.pop('error', None) or "Subrequest failed"
        code = kwargs.pop('code', None) or 503
        
        message = kwargs.pop('message', None)
        base_message = f"Subrequest #{response.request.request_id} '{response.request.method} {response.request.url}' failed"
        if (expected_codes is not None):
            if (message is None):
                expected = f"one of: {', '.join(f'{c}' for c in expected_codes)}" if (len(expected_codes) > 1) else f"{next(iter(expected_codes))}"
                message = f"{base_message}, got unexpected status code: expected {expected}, got {response.code}."
                try:
                    parsed = json.loads(response.body)
                except Exception:
                    pass
                else:
                    if (isinstance(parsed, dict)):
                        _err = parsed.get('error')
                        _msg = parsed.get('message')
                        
                        if (_err and _msg):
                            message += " " f"Error: '{_err} ({_msg})'"
                        elif (_err or _msg):
                            message += " " f"Error: '{_err or _msg}'"
                
                if (response.code == 599): message += f" ({str(response.error)})"
            if (error_code is None): error_code = SubrequestFailedErrorCodes.StatusCodeMismatch
        
        if (expected_mime_type is not None):
            if (message is None): message = f"{base_message}, got unexpected mime type: expected '{expected_mime_type}', got '{','.join(response.headers.get_list('Content-Type'))}'"
            if (error_code is None): error_code = SubrequestFailedErrorCodes.MimeTypeMismatch
        
        if (error_code is None): error_code = SubrequestFailedErrorCodes.Other
        if (message is None): message = base_message
        
        self.error_code = error_code
        self.response = response
        super().__init__(code=code, error=error, message=message, subrequest_id=response.request.request_id, error_code=error_code, **kwargs)

__all__ = \
[
    'ServerError',
    'SubrequestFailedError',
    'SubrequestFailedErrorCodes',
]
