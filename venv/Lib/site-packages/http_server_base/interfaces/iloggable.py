from abc import ABC
from types import TracebackType
from typing import *

from tornado.httpclient import HTTPClientError
from tornado.web import HTTPError as HTTPServerError

from http_server_base.tools.logging import ExtendedLogger, logging_method, get_logger

class ILoggable(ABC):
    logger_name: str
    logger: ExtendedLogger = None
    logger_class: Type[ExtendedLogger] = None
    
    #region Logging
    def initialize_logger(self, *args, base_logger: ExtendedLogger = None, **kwargs):
        if (base_logger is None):
            base_logger = get_logger(self.logger_name)
        if (self.logger_class is not None):
            # noinspection PyTypeChecker
            logger = self.logger_class(*args, base_logger, **kwargs)
        else:
            logger = base_logger
        self.logger = logger
    
    @logging_method
    def log_exception(self, error_type, error, trace: TracebackType):
        _at = ""
        if (trace):
            from traceback import extract_tb
            frame = extract_tb(trace)[0]
            _at =f" at {frame.filename}:{frame.lineno}"
        if (isinstance(error_type, type)):
            error_type = error_type.__name__
        msg = f"{error_type}{_at}: {error}"
        if (isinstance(error, Warning)):
            self.logger.warning(f"{error_type}: {error}")
        elif (isinstance(error, (HTTPServerError, HTTPClientError))):
            self.logger.error(msg)
        else:
            self.logger.exception(f"Uncaught exception {msg}", exc_info=(error_type, error, trace))
    #endregion

__all__ = \
[
    'ILoggable',
]
