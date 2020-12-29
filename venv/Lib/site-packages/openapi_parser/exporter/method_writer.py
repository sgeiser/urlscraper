from enum import Enum, auto
from functools import partial
from typing import *
from typing import Dict

from functional import OptionNone, Some, Option

from openapi_parser.model import ModelEndpoint, ModelClass, ParameterType, ModelSchema
from openapi_parser.util.utils import StrIO
from .abstract_writer import Writer, yielder, writer
from .attribute_writer import AttributeWriter
from .description_writer import DescriptionWriter
from .footer_writer import Exporting

class MethodType(Enum):
    Function = auto()
    ClassMethod = auto()
    StaticMethod = auto()
    RegularMethod = auto()


class MethodWriter(Exporting, AttributeWriter, DescriptionWriter, Writer):
    M = Union[ModelSchema, Type, Any]
    def write_method_head(self, method_name: str, params: List[str] = None, return_type: Union[Option[M], Optional[M]] = OptionNone, *, method_type: MethodType = MethodType.Function, asynchronous: bool = False) -> Iterator[str]:
        if (params is None):
            params = list()
        if (not isinstance(return_type, Option)):
            return_type = Option.from_optional(return_type)
        
        if (method_type == MethodType.Function):
            pass
        elif (method_type == MethodType.RegularMethod):
            params.insert(0, 'self')
        elif (method_type == MethodType.ClassMethod):
            yield '@classmethod'
            params.insert(0, 'cls')
        elif (method_type == MethodType.StaticMethod):
            yield '@staticmethod'
        
        if (asynchronous):
            def_keyword = 'async def'
        else:
            def_keyword = 'def'
        
        yield from self.smart_constructor(f'{def_keyword} {method_name}', *params, suffix=return_type.map(' -> {}'.format).get_or_else('') + ':')
    
    def dump_endpoint_description(self, method: ModelEndpoint, *, compact: bool = False) -> Iterator[str]:
        gen = partial(self.generate_endpoint_description, method)
        yield from self.smart_description(gen, compact=compact)
    
    def generate_endpoint_description(self, method: ModelEndpoint, *, compact: bool):
        def extra_gen():
            params = method.all_parameters
            if (params):
                yield "Arguments:"
                with self.indent():
                    for p in params:
                        p_name, p_cls, p_value, _ = self.parse_attribute(p.name, p.schema, is_required=p.required)
                        yield f'{p_name}' + ':' + p_cls.map(' `{}`'.format).get_or_else('') + p_value.map(', default: `{}`'.format).get_or_else('') + '.'
                        with self.indent():
                            yield from self.text_block(p_value.map(lambda _: 'Optional.').get_or_else('**REQUIRED.**') + ' ' + Option(p.description).get_or_else(''))
                        yield
                    
                    if (method.request_body is not None):
                        media_type, media_data = method.regular_request_parser
                        p_name, p_cls, p_value, _ = self.parse_attribute('data', media_data.schema, is_required=True)
                        yield f'{p_name}' + ':' + p_cls.map(' `{}`'.format).get_or_else('') + '.'
                        with self.indent():
                            yield f"**REQUIRED.** Request body" + (" of '{media_type}' media-type" if media_data != '*/*' else '') + Option(media_data).flat_map(lambda m: Option(m.encoding)).map(" (encoding: '{}')".format).get_or_else('')
                            if (media_data is not None and media_data.schema is not None):
                                yield from self.text_block(media_data.schema.summary, compact=True)
                                yield from self.text_block(media_data.schema.description, compact=True)
                        yield
            
            _, resp = method.regular_response
            if (resp is not None):
                _, media_data = resp.regular_request_parser
                if (media_data is not None and media_data.schema is not None):
                    yield "Returns:"
                    with self.indent():
                        _, r_cls, _, _ = self.parse_attribute('response', media_data.schema, is_required=True)
                        yield from self.text_block(r_cls.map('`{}`. '.format).get_or_else('') + Option(resp.description).get_or_else(''), compact=True)
                        yield from self.text_block(media_data.schema.summary, compact=True)
                        yield from self.text_block(media_data.schema.description, compact=True)
                    yield
        
        yield from self.generate_item_description(item=method, item_type='endpoint', compact=compact, extra_gen=extra_gen())
    
    def dump_endpoint(self, endpoint: ModelEndpoint, endpoint_path: str, http_method: str, method_type: MethodType = MethodType.Function, asynchronous: bool = False) -> Iterator[str]:
        method_name = self.method_name_pretty(endpoint.operation_id)
        
        params: List[str] = list()
        
        required_path_params: List[str] = list()
        optional_path_params: List[str] = list()
        header_params: List[str] = list()
        query_params: List[str] = list()
        
        path_params_map: Dict[str, str] = dict()
        header_params_map: Dict[str, str] = dict()
        query_params_map: Dict[str, str] = dict()
        for p in endpoint.all_parameters:
            if (p.schema is None):
                pass
            elif (p.schema.read_only):
                continue
            
            name, f_type, f_value, _ = self.parse_attribute(p.name, p.schema, is_required=p.required)
            is_optional = f_value.is_empty
            
            item = self.join_attribute(name, f_type, f_value)
            v = name
            if (p.schema is not None):
                encoder = self.extract_coder(p.schema, 'encoder')
                if (encoder is not None):
                    v = f'{encoder}({v})'
                elif (p.schema.cls != str):
                    v = f'str({v})'
            
            if (p.parameter_type == ParameterType.Path):
                path_params_map[p.name] = f'{{{name}}}'
                if (is_optional):
                    required_path_params.append(item)
                else:
                    optional_path_params.append(item)
            elif (p.parameter_type == ParameterType.Query):
                query_params_map[p.name] = v
                query_params.append(item)
            elif (p.parameter_type == ParameterType.Header):
                header_params_map[p.name] = v
                header_params.append(item)
            elif (p.parameter_type == ParameterType.Cookie):
                # ToDo: Cookie Params
                pass
        
        fetch_args = dict()
        fetch_method = 'fetch'
        fetch_args['request'] = 'f' + repr(endpoint_path.format_map(path_params_map))
        if (http_method != 'get'):
            fetch_args['method'] = repr(http_method.upper())
        if (query_params_map):
            fetch_args['query'] = f"filter_out_smart({self.dict_constructor(**query_params_map)})"
        if (header_params_map):
            fetch_args['headers'] = f"filter_out_smart({self.dict_constructor(**header_params_map)})"
        
        if (endpoint.request_body is not None):
            body_default_media_type, body_default_model = endpoint.regular_request_parser
            if (body_default_model is not None and body_default_model.schema is not None):
                _, body_type, body_value, _ = self.parse_attribute(method_name, body_default_model.schema, is_required=True)
            elif body_default_model is not None:
                body_type = Some('bytes')
                body_value = OptionNone
            else:
                body_type = OptionNone
                body_value = OptionNone
            
            if ('*' not in body_default_media_type and body_type.is_defined):
                fetch_args['encode_body'] = repr(body_default_media_type)
            
            fetch_args['body'] = 'data'
            body_param = Some(self.join_attribute('data', body_type, body_value))
        else:
            body_param = OptionNone
            body_value = OptionNone
        
        params.extend(required_path_params)
        if (body_value.is_empty):
            body_param.map(params.append)
        params.extend(optional_path_params)
        if (body_value.non_empty):
            body_param.map(params.append)
        if (query_params or header_params):
            params.append('*')
        params.extend(query_params)
        params.extend(header_params)
        
        default_resp_code, default_resp = endpoint.regular_response
        return_type = OptionNone
        if (default_resp is not None):
            default_media_type, default_model = default_resp.regular_request_parser
            if (default_model is not None and default_model.schema is not None):
                _, return_type, _, _ = self.parse_attribute(method_name, default_model.schema, is_required=True)
            elif default_model is not None:
                return_type = Some('bytes')
        else:
            default_media_type, default_model = None, None
        
        local_vars = OptionNone
        if (return_type == Some('bytes')):
            local_vars = Some([ '_', 'resp' ])
            fetch_method = 'fetch_binary_data'
        elif (return_type.non_empty and default_model is not None and default_model.schema is not None and isinstance(default_model.schema.cls, ModelClass)):
            local_vars = Some([ '_', 'resp' ])
            fetch_method = 'fetch_json_model'
            fetch_args['model'] = return_type.get
        elif (return_type.non_empty):
            local_vars = Some([ '_', 'resp' ])
            fetch_method = 'fetch_json'
        
        if (default_media_type != '*/*'):
            fetch_args['expected_content_type'] = repr(default_media_type)
        if (default_resp_code is not None):
            if (default_resp_code.isdigit()):
                default_resp_code = int(default_resp_code)
            fetch_args['expected_codes'] = f'[ {default_resp_code!r} ]'
        
        p0 = local_vars.map(', '.join).map('{} ='.format)
        p1 = Some('await') if asynchronous else OptionNone
        prefix = ' '.join(opt.get for opt in [ p0, p1, Some('self') ] if opt.non_empty)
        
        yield from self.write_method_head(method_name, params, return_type, method_type=method_type, asynchronous=asynchronous)
        with self.indent():
            yield from self.dump_endpoint_description(endpoint)
            yield from self.smart_constructor(f'{prefix}.{fetch_method}', **fetch_args)
            if (return_type.non_empty):
                yield 'return resp'
        yield
    
    # region Writers
    @yielder
    def yield_endpoint(self, e: ModelEndpoint, endpoint_path: str, http_method: str) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_endpoint(e, endpoint_path, http_method)
    
    @overload
    def write_endpoint(self, e: ModelEndpoint, endpoint_path: str, http_method: str) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_endpoint(self, e: ModelEndpoint, endpoint_path: str, http_method: str, *, file: StrIO) -> None:
        pass
    @writer
    def write_endpoint(self, e: ModelEndpoint, endpoint_path: str, http_method: str) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_endpoint(e, endpoint_path, http_method)
    # endregion


__all__ = \
[
    'MethodType',
    'MethodWriter',
]
