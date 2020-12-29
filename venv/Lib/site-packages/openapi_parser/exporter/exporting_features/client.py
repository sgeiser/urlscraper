from typing import *
from urllib.parse import urlparse, ParseResult

from http_server_base import SubrequestClient
from http_server_base.model import IEncoder, FilteringJsonEncoder
from http_server_base.tools import HttpSubrequest, RequestLogger
from tornado.httpclient import HTTPRequest

class BaseClient(SubrequestClient):
    server: str
    logger_name: str = __name__
    model_encoder: Type[IEncoder] = FilteringJsonEncoder
    
    def __init__(self, server: str):
        super().__init__()
        self.server = server
        self.initialize_logger()
        self.logger = RequestLogger(None, self.logger)
    
    async def _fetch__form_request(self, request: Union[str, HTTPRequest, HttpSubrequest], **kwargs) -> HttpSubrequest:
        request = await super()._fetch__form_request(request, **kwargs)
        request = await self._fetch__form_request__add_server(request)
        return request
    
    async def _fetch__form_request__add_server(self, request: HttpSubrequest) -> HttpSubrequest:
        parsed: ParseResult = urlparse(request.url)
        if (not parsed.hostname):
            request.url = self.server + request.url
        
        return request


__export__ = \
[
    'BaseClient._fetch__form_request',
    'BaseClient._fetch__form_request__add_server',
]
