import json
from typing import *
from urllib.parse import urlencode

from dataclasses_json.core import Json
from tornado.httpclient import HTTPRequest, HTTPResponse

from .logging import RequestLogger, ExtendedLogger, get_logger

class HttpSubrequest(HTTPRequest):
    request_id: str
    parent_request_id: str
    logger: RequestLogger
    
    def __init__ \
    (
        self,
        url: Union[str, HTTPRequest],
        *args,
        query: Union[dict, str, None] = None,
        body: Any = None,
        files: Optional[Iterable[Tuple[str, str, AnyStr, str]]] = None,
        request_id: str = None,
        parent_request_id: str = None,
        base_logger: ExtendedLogger = None,
        encode_body: Optional[str],
        model_encoder = None,
        **kwargs,
    ):
        if (isinstance(url, HTTPRequest)):
            self.__dict__ = url.__dict__.copy()
            if (body is None):
                body = self.body
        else:
            super().__init__(url, *args, body=body if (not encode_body) else None, **kwargs)
        
        if (query):
            self.encode_query(query=query)
        if (encode_body):
            self.encode_body(body=body, files=files, encode_body=encode_body, model_encoder=model_encoder)
        
        self.request_id = request_id
        self.parent_request_id = parent_request_id
        if (base_logger is None):
            # noinspection PyTypeChecker
            base_logger: ExtendedLogger = get_logger('http_server.subrequests')
        
        self.logger = RequestLogger(self, base_logger)
    
    def encode_query(self, *, query: Union[str, Dict[str, Any], None]):
        if (query is not None):
            if (not isinstance(query, str)):
                query = urlencode(query)
            url = self.url
            url += '&' if ('?' in url) else '?'
            url += query
            self.url = url
    
    def encode_body(self, *, body: Optional[AnyStr], files: Optional[Iterable[Tuple[str, str, AnyStr, str]]], encode_body: Optional[str], model_encoder):
        content_type = encode_body
        if (encode_body is None):
            pass
        elif (isinstance(body, bytes)):
            pass
        elif (body is not None and encode_body.startswith('text/')):
            if (not isinstance(body, str)):
                body = str(body)
            body = body.encode('utf8')
        elif (encode_body.startswith('application/') or encode_body.startswith('multipart/')):
            if (body is None):
                encoded_obj = None
            elif (isinstance(body, list)):
                if (body):
                    if (isinstance(body[0], Json.__args__)):
                        encoded_obj = body
                    elif (model_encoder is None):
                        raise ValueError(f"Cannot encode body '{body}' without an encoder")
                    else:
                        encoded_obj = model_encoder.encode_many(type(body[0]), body)
                else:
                    encoded_obj = [ ]
            elif (isinstance(body, Json.__args__)):
                encoded_obj = body
            elif (model_encoder is not None):
                encoded_obj = model_encoder.encode_single(type(body), body)
            else:
                raise ValueError(f"Cannot encode body '{body}' without an encoder")
            
            if (encode_body.startswith('multipart/')):
                if (isinstance(encode_body, dict)):
                    encode_body = ((str(k), str(v)) for k, v in encode_body.items())
                content_type_extensions, body = self.encode_multipart_data(fields=encode_body, files=files)
                content_type = content_type + '; ' + content_type_extensions
            elif (encode_body == 'application/json'):
                body = json.dumps(encoded_obj)
            elif (encode_body == 'application/x-www-form-urlencoded'):
                if (isinstance(encode_body, dict)):
                    body = urlencode(encode_body).encode()
                else:
                    raise ValueError(f"Unsupported type for encoding '{encode_body}': '{type(encode_body)}'")
            else:
                raise ValueError(f"Unsupported mime-type for encoding: '{encode_body}'")
        else:
            raise ValueError(f"Unsupported mime-type for encoding: '{encode_body}'")
        
        self.body = body
        if (content_type is not None):
            self.headers['Content-Type'] = content_type
    
    @classmethod
    def encode_multipart_data(cls, fields: Optional[Iterable[Tuple[str, str]]] = None, files: Optional[Iterable[Tuple[str, str, AnyStr, str]]] = None, *, boundary: AnyStr = '--------------------------F1ELD$_$PL117ER__$$', line_separator: AnyStr = b'\r\n', encoding: str = 'utf-8') -> Tuple[str, bytes]:
        """
        :param fields:
        (name, value) tuple.
        Elements for regular form fields.
        
        :param files:
        (name, filename, value, content_type) tuple.
        Elements for data to be uploaded as files.
        
        :param boundary:
        Boundary to be used in the form-data
        :param line_separator:
        Line separator to be used. Default: CRLF
        :param encoding:
        Encoding to be used. Default: utf-8
        
        :return:
        Returns (content-type extensions, body)
        """
        
        if (fields is None):
            fields = [ ]
        if (files is None):
            files = [ ]
        
        if (isinstance(boundary, str)):
            boundary = boundary.encode(encoding)
        if (isinstance(line_separator, str)):
            line_separator = line_separator.encode(encoding)
        
        data: List[bytes] = list()
        for (key, value) in fields:
            data.append(b'--' + boundary)
            data.append(f'Content-Disposition: form-data; name="{key}"'.encode(encoding))
            data.append(b'')
            data.append(value)
        for (key, filename, value, content_type) in files:
            filename = filename.encode(encoding)
            data.append(b'--' + boundary)
            data.append((f'Content-Disposition: form-data; name="{key}"; filename="{filename}"').encode(encoding))
            data.append((f'Content-Type: {content_type}').encode(encoding))
            data.append(b'')
            if (isinstance(value, str)):
                value = value.encode(encoding)
            if (isinstance(value, bytes)):
                data.append(value)
            else:
                raise TypeError(f"File '{filename}' ('{key}' field; '{content_type}'): value must be either str or bytes, not '{type(value)}'")
        
        data.append(b'--' + boundary + b'--')
        data.append(b'')
        body = line_separator.join(data)
        extensions = f'boundary={boundary.decode(encoding)}; charset={encoding}'
        
        return extensions, body

class HttpSubrequestResponse(HTTPResponse):
    request: HttpSubrequest
    
    def __init__(self, *args, **kwargs):
        if (args and isinstance(args[0], HTTPResponse)):
            self.__dict__ = args[0].__dict__.copy()
        else:
            super().__init__(*args, **kwargs)

__all__ = \
[
    'HttpSubrequest',
    'HttpSubrequestResponse',
]
