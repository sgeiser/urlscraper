import json
import random
import re
import string
from abc import ABC
from asyncio import sleep
from json import JSONDecodeError
from math import log2
from typing import *

from tornado.httpclient import HTTPRequest, AsyncHTTPClient
from tornado.httputil import HTTPHeaders
from tornado.web import HTTPError

from .error_matcher import ErrorMatcher
from .model import IEncoder, EncoderError
from .request_logger_client import RequestLoggerClient
from .tools.config_loader import ConfigLoader
from .tools.errors import SubrequestFailedErrorCodes, SubrequestFailedError
from .tools.extensions import revrange
from .tools.logging import RequestLogger
from .tools.subrequest_classes import HttpSubrequest, HttpSubrequestResponse
from .tools.types import JsonSerializable

T = TypeVar('T')
class SubrequestClient(RequestLoggerClient, ErrorMatcher, ABC):
    
    logger: RequestLogger
    model_encoder: Union[IEncoder[T], Type[IEncoder[T]]] = IEncoder
    _async_http_client: AsyncHTTPClient = None
    request_id_header_name: str = 'X-Request-Id'
    
    @property
    def async_http_client(self) -> AsyncHTTPClient:
        if (self._async_http_client is None):
            self._async_http_client = AsyncHTTPClient()
        
        return self._async_http_client
    
    #region Fetching
    async def _fetch__form_request(self, request: Union[str, HTTPRequest], *, add_request_id: bool, expected_content_type: Optional[str] = None, **kwargs) -> HttpSubrequest:
        if (not isinstance(request, HttpSubrequest)):
            request = HttpSubrequest(url=request, request_id=self.generate_request_id(), parent_request_id=getattr(self, 'request_id', None), base_logger=self.logger, model_encoder=self.model_encoder, **kwargs)
        
        if (add_request_id):
            request = await self._fetch__form_request__add_request_id(request)
        
        if (expected_content_type):
            request = await self._fetch__form_request__add_accept_header(request, expected_content_type=expected_content_type)
        
        return request
    async def _fetch__form_request__add_request_id(self, request: HttpSubrequest) -> HttpSubrequest:
        if (not isinstance(request.headers, HTTPHeaders)):
            request.headers = HTTPHeaders(request.headers)
        request.headers.add(self.request_id_header_name, request.request_id)
        return request
    async def _fetch__form_request__add_accept_header(self, request: HttpSubrequest, *, expected_content_type: str) -> HttpSubrequest:
        if (not isinstance(request.headers, HTTPHeaders)):
            request.headers = HTTPHeaders(request.headers)
        request.headers.setdefault('Accept', expected_content_type)
        return request
    async def _fetch__define_parameters(self, request: HttpSubrequest, *, configuration_prefix: str, config_name: str, attempts: Optional[int] = None, exponential_retries: Optional[bool] = None, retry_max_time: Union[int, float, None] = None, retry_timeout: Union[int, float, None], intercept_connection_errors: Optional[bool] = None, **kwargs):
        if (retry_timeout is None):
            retry_timeout = ConfigLoader.get_from_config(f'{configuration_prefix}retries/timeout', config_name, default=100)
        if (not isinstance(retry_timeout, (int, float))):
            raise ValueError(f"Retry timeout should be int or float, not {type(retry_timeout)}.")
        elif (retry_timeout < 0):
            raise ValueError(f"Retry timeout should not be negative, got {retry_timeout}.")
        
        if (exponential_retries is None):
            exponential_retries = ConfigLoader.get_from_config(f'{configuration_prefix}retries/exponentialRetries', config_name, default=True)
        
        if (attempts is None and retry_max_time is None):
            attempts = ConfigLoader.get_from_config(f'{configuration_prefix}retries/maxAttempts', config_name, default=1)
        elif (attempts is None):
            attempts = int(retry_max_time / retry_timeout) + 1
            if (exponential_retries):
                attempts = log2(attempts) + 1
            attempts = int(attempts)
        if (not isinstance(attempts, int)):
            raise ValueError(f"Attempts should be int, not {type(attempts)}.")
        elif (attempts < 1):
            raise ValueError(f"Attempts should be 1 or higher, not {attempts}.")
        
        return dict(attempts=attempts, exponential_retries=exponential_retries, retry_timeout=retry_timeout, intercept_connection_errors=intercept_connection_errors)
    async def _fetch__retries_logic(self, request: HttpSubrequest, *, attempts, exponential_retries, intercept_connection_errors, retry_timeout):
        response = None
        _to = retry_timeout
        for i in revrange(attempts):
            _last_attempt = i == 0
            _intercept_connection_errors = intercept_connection_errors if (_last_attempt) else False
            
            try:
                response = await self._fetch__fetch_request(request, intercept_connection_errors=_intercept_connection_errors)
            except Exception as e:
                if (_last_attempt):
                    raise
                else:
                    request.logger.warning(f"Subrequest failed (reason: {e}), retrying in {_to}ms...")
                    await sleep(_to / 1000)
                    if (exponential_retries):
                        _to *= 2
            else:
                request.logger.trace(f"Request finished with status code {response.code} (is last attempt: {_last_attempt}; intercept connection errors: {_intercept_connection_errors}, attempt: {attempts - i} of {attempts})")
                break
        return response
    async def _fetch__fetch_request(self, request: HttpSubrequest, intercept_connection_errors: bool) -> HttpSubrequestResponse:
        request.logger.debug(f"Request: {request.method} {request.url}")
        _client = self.async_http_client
        
        future = _client.fetch(request, raise_error=False)
        try:
            response = await future
        except Exception as e:
            if (intercept_connection_errors):
                response = self.match_error(request, e)
            else:
                raise
        
        response = HttpSubrequestResponse(response)
        request.logger.debug(f"Response: {response.request.method} {response.request.url}; Code: {response.code}; Content-length: {len(response.body or '')}")
        self.dump_response(response, request_name=f"Subrequest {request.request_id}", logger=request.logger, prefix='resp')
        return response
    async def _fetch__check_response__content_type_matching(self, response: HttpSubrequestResponse, *, expected_content_type: Optional[str]) -> Optional[SubrequestFailedError]:
        if (expected_content_type is None):
            return None
        elif (expected_content_type == '*/*'):
            return None
        elif ('Content-Type' not in response.headers):
            return SubrequestFailedError(response, message="Missing 'Content-Type' header in the response", expected_mime_type=expected_content_type)
        else:
            for h in response.headers.get_list('Content-Type'):
                h = h.partition(';')[0]
                if (re.fullmatch(expected_content_type.replace('*', r'[^/]+'), h)):
                    return None
            
            return SubrequestFailedError(response, message=f"Missing '{expected_content_type}' in 'Content-Type' headers of the response ({','.join(response.headers.get_list('Content-Type'))})", expected_mime_type=expected_content_type)
    async def _fetch__check_response(self, response: HttpSubrequestResponse, *, expected_codes: Collection[int], expected_content_type: Optional[str]):
        response.request.logger.trace("Checking response...")
        exception = None
        
        if (exception is None and response.code not in expected_codes):
            exception = SubrequestFailedError(response, expected_codes=expected_codes)
        
        if (exception is None and expected_content_type):
            exception = await self._fetch__check_response__content_type_matching(response, expected_content_type=expected_content_type)
        
        if (exception is not None):
            response.request.logger.warning(str(exception))
            if (response.error and not isinstance(response.error, HTTPError)):
                response.request.logger.warning(f"Base error: {str(response.error)}")
            raise exception
    async def fetch \
    (
        self,
        request: Union[str, HTTPRequest],
        *,
        
        # Retries
        attempts: int = None,
        retry_timeout: int = None,
        retry_max_time: int = None,
        exponential_retries: bool = None,
        
        # Response Validation
        intercept_connection_errors: bool = True,
        raise_error: bool = True,
        expected_codes: Union[int, Collection[int], Collection[str]] = 200,
        expected_content_type: str = None,
        
        # Data
        query: Union[str, Dict[str, Any], None] = None,
        files: Optional[Iterable[Tuple[str, str, AnyStr, str]]] = None,
        
        # Options
        configuration_prefix: Union[str, Tuple[str, str]] = 'HTTP/',
        add_request_id: bool = True,
        encode_body: Optional[str] = None,
        **kwargs,
    ) -> HttpSubrequestResponse:
        """
        Fetches the specified request and asynchronously returns response.
        Minorly logs both request and response objects.
        Response is the instance of HttpSubrequestResponse (child of HTTPResponse).
        
        If the `intercept_connection_errors` option is set, the default errors will be intercepted by the client.
        If the `raise_error` option is set, the request status code is checked to be one of `expected_codes` parameter (parameters like `"2xx"` are supported).
        If the `raise_error` option is set, the mime type of response will be checked to have value of `expected_content_type` parameter (parameters like `"application/*"` are supported).
        If the `add_request_id` option is set, the request object will have appropriate.
        If the `encode_body` is set, the request body will be encoded using the given mime-type.
        All other parameters are nested from the original `tornado.httpclient.AsyncHTTPClient.fetch()`.
        
        Retries
        :param attempts: int
        A maximum number of attempts for a request.
        Default: calculated from retry_max_time, or from configuration (parameter 'retries/maxAttempts'), or 1
        :param retry_timeout: int
        An initial wait time (in ms) before the first retry.
        Default: from configuration (parameter 'retries/timeout'), or 100ms
        :param retry_max_time: int
        Max total wait time (in ms) for the request retries.
        If both attempts and retry_max_time are present, attempts is prioritized.
        Default: calculated from attempts.
        :param exponential_retries: bool
        If set, each of the next retries wait intervals will be twice as longer than previous.
        Default: from configuration (parameter 'retries/exponentialRetries'), or True
        
        Response validation:
        :param intercept_connection_errors:  bool
        :param request: str or HTTPRequest
        :param raise_error: bool
        :param expected_codes: int, Collection[int], or Collection[str]
        :param expected_content_type: str or None
        
        Data:
        :param files: Iterable over (name: str, filename: str, value: AnyStr, content_type: str) tuple.
        If set in combination with encode_body='multipart/...', will attach these files
        :param query: str or Mapping
        If set, will encode the given query as query string and add it to the initial request
        
        Options:
        :param configuration_prefix: str, or tuple [str, str]
        A prefix for the subrequests configuration.
        If tuple is given, the second argument is counted as config name.
        Default: 'HTTP/'
        :param add_request_id: bool
        If True, a request id will be added to the subrequest
        Default: True
        :param encode_body: str
        If set, will encode the body unless it is missing or it is already encoded.
        
        :raises: SubrequestFailedError
        :raises: ValueError
        :returns: HttpSubrequestResponse
        """
        
        if (isinstance(configuration_prefix, tuple)):
            configuration_prefix, config_name = configuration_prefix
        else:
            config_name = 'main'
        
        if (expected_codes is None):
            expected_codes = [ 200 ]
        elif (isinstance(expected_codes, int)):
            expected_codes = [ expected_codes ]
        else:
            _items = list()
            for e in expected_codes:
                if (isinstance(e, int)):
                    _items.append(e)
                elif (isinstance(e, str)):
                    if (e.isdigit()):
                        _items.append(int(e))
                    elif (re.fullmatch(r'\dxx', e)):
                        d1 = int(e[0])
                        _items.extend(range(d1 * 100, (d1 + 1) * 100))
                    else:
                        raise ValueError(f"Invalid string status-code: '{e}', expected either '201'-like or '2xx'-like.")
                else:
                    raise ValueError(f"Only integer and string status-codes are supported, got '{e}' ({type(e)})")
            expected_codes = _items
        
        request = await self._fetch__form_request(request, add_request_id=add_request_id, query=query, encode_body=encode_body, files=files, expected_content_type=expected_content_type, **kwargs)
        params = await self._fetch__define_parameters(request, attempts=attempts, config_name=config_name, configuration_prefix=configuration_prefix, exponential_retries=exponential_retries, retry_max_time=retry_max_time, retry_timeout=retry_timeout, intercept_connection_errors=intercept_connection_errors, **kwargs)
        response = await self._fetch__retries_logic(request, **params)
        
        if (raise_error):
            await self._fetch__check_response(response, expected_codes=expected_codes, expected_content_type=expected_content_type)
        
        return response
    async def _fetch_json__parse_json(self, response: HttpSubrequestResponse, json_load_options: Dict[str, Any]) -> JsonSerializable:
        if (response.body is None):
            raise SubrequestFailedError(message="Server responded empty body while JSON was expected to be", error_code=SubrequestFailedErrorCodes.InvalidResponseBody, response=response)
        
        if (json_load_options is None):
            json_load_options = dict()
        
        try:
            resp_data = response.body.decode()
            resp_json: Dict[str, Any] = json.loads(resp_data, **json_load_options)
        except JSONDecodeError as e:
            raise SubrequestFailedError(message=f"Cannot decode JSON from the response: '{response.body}'", server_response=str(response.body), error_code=SubrequestFailedErrorCodes.InvalidResponseBody, response=response) from e
        except Exception as e:
            raise SubrequestFailedError(code=500, error="Unknown Error", message=f"Unknown error: {e}", response=response) from e
        else:
            return resp_json
    async def _fetch_json__extract_error(self, extracted_json: JsonSerializable) -> Optional[str]:
        if (isinstance(extracted_json, dict)):
            return extracted_json.get('reason') or extracted_json.get('error') or (extracted_json.get('errors') and extracted_json['errors'][0]) or extracted_json.get('message')
        elif (isinstance(extracted_json, str)):
            return extracted_json
        else:
            return None
    async def _fetch__reword_exception(self, error: SubrequestFailedError, json_load_options: Dict[str, Any]):
        try:
            resp_json = await self._fetch_json__parse_json(error.response, json_load_options)
        except Exception as exc:
            message = f"Unable to extract error message: {exc}"
        else:
            message = await self._fetch_json__extract_error(resp_json)
        if (message is not None):
            error.reword(message=message)
    async def fetch_json(self, request: Union[str, HTTPRequest], *, check_content_type_header: bool = True, json_load_options: Dict[str, Any] = None, **kwargs) -> Tuple[HttpSubrequestResponse, JsonSerializable]:
        """
        Fetches the specified request for the JSON data and asynchronously returns both response and loaded JSON object.
        Minorly logs both request and response objects.
        Response is the instance of HttpSubrequestResponse (child of HTTPResponse).
        
        The `raise_error` is always overridden to True.
        If the `check_content_type_header` option is set, the request headers will be checked to have 'Content-Type: application/json'.
        The `json_load_options` parameter is expanded to keyword-params of the json.loads() method.
        All other parameters are nested from the `fetch()` method above.
        
        :param request: str or HTTPRequest
        :param check_content_type_header: bool
        :param json_load_options: kwargs 
        
        :raises: SubrequestFailedError
        :returns: Tuple[HttpSubrequestResponse, JsonSerializable]
        """
        
        kwargs.pop('raise_error', None)
        kwargs.pop('expected_content_type', None)
        try:
            response = await self.fetch(request, raise_error=True, expected_content_type='application/json' if (check_content_type_header) else None, **kwargs)
        except SubrequestFailedError as e:
            await self._fetch__reword_exception(e, json_load_options)
            raise
        
        else:
            resp_json = await self._fetch_json__parse_json(response, json_load_options)
            return response, resp_json
    async def _fetch_json_model__parse_model(self, response: HttpSubrequestResponse, data: JsonSerializable, model: Type[T], encoder: Union[IEncoder, Type[IEncoder]]) -> T:
        try:
            parsed = encoder.decode_smart(model, data)
        except EncoderError as e:
            resp_data = response.body.decode()
            raise SubrequestFailedError(response, message=f"Cannot parse model '{model.__name__}' from the response '{resp_data}': {e}", server_response=str(resp_data), error_code=SubrequestFailedErrorCodes.InvalidResponseBody) from e
        except Exception as e:
            self.logger.exception(f"Unknown error: {e}")
            raise SubrequestFailedError(response, code=500, error="Unknown Error", message=f"Unknown error: {e}") from e
        
        return parsed
    async def fetch_json_model(self, request: Union[str, HTTPRequest], model: Type[T], encoder: Union[IEncoder, Type[IEncoder]] = None, **kwargs) -> Tuple[HttpSubrequestResponse, T]:
        """
        Fetches the specified request for the serialized JSON data and asynchronously returns both response and deserialized object.
        Minorly logs both request and response objects.
        Response is the instance of HttpSubrequestResponse (child of HTTPResponse).
        
        The `raise_error` is always overridden to True.
        All other parameters are nested from the `fetch_json()` method above.
        
        :param request: str or HTTPRequest
        :param model: Type[T] - Model for the request response
        :param encoder: IEncoder[T] or Type[IEncoder[T]] - Encoder for model
        
        :raises SubrequestFailedError
        :return Tuple[HttpSubrequestResponse, T] - response object and parsed deserialized response body
        """
        
        response, j = await self.fetch_json(request, **kwargs)
        if (encoder is None):
            encoder = self.model_encoder
        if (encoder is None or encoder is IEncoder):
            raise ValueError("No encoder specified")
        parsed = await self._fetch_json_model__parse_model(response, j, model, encoder=encoder)
        
        return response, parsed
    async def fetch_binary_data(self, request: Union[str, HTTPRequest], **kwargs) -> Tuple[HttpSubrequestResponse, bytes]:
        """
        Fetches the specified request for the binary data and asynchronously returns both response and loaded bytes.
        Minorly logs both request and response objects.
        Response is the instance of HttpSubrequestResponse (child of HTTPResponse).
        
        The `raise_error` is always overridden to True.
        All other parameters are nested from the `fetch()` method above.
        
        :param request: str or HTTPRequest
        
        :raises: SubrequestFailedError
        :returns: Tuple[HttpSubrequestResponse, bytes]
        """
        
        kwargs.pop('raise_error', None)
        try:
            response = await self.fetch(request, raise_error=True, **kwargs)
        except SubrequestFailedError as e:
            await self._fetch__reword_exception(e, dict())
            raise
        
        if (response.body is None):
            raise SubrequestFailedError(response, message="Server responded empty body", error_code=SubrequestFailedErrorCodes.InvalidResponseBody)
        
        return response, response.body
    #endregion
    
    @classmethod
    def generate_random_string(cls, N):
        return ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=N))
    def generate_request_id(self) -> str:
        return "{0:x}".format(random.randint(0x10000000, 0xffffffff))

class SimpleSubrequestClient(SubrequestClient):
    logger_name: str = 'http-server-base.subrequest-client.impl'
    def __init__(self):
        super().__init__()
        self.initialize_logger()


__all__ = \
[
    'SimpleSubrequestClient',
    'SubrequestClient',
]
