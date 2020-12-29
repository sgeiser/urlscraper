import json
import re
from datetime import datetime
from functools import partial
from typing import *

import yaml
from functional import Option

from openapi_parser.model import *
from openapi_parser.util.typing_proxy import *
from .date_formats import DateFormatName
from .errors import *
from .filters import *
from .inheritance_support import InheritanceFilter
from .model_impl import *
from .path import split_path_right, split_path_left

M = TypeVar('M', bound=Model)
T = TypeVar('T')
def smart_loader(loader: Callable = None, *, support_ref_field: bool = True, default_path: Optional[str] = None):
    def wrapper(func: Callable):
        def _load_item(self: 'OpenApiParser', item_data: Dict[str, Any], path: str, *, is_top_level: bool = False, **kwargs):
            if (support_ref_field and '$ref' in item_data):
                # noinspection PyTypeChecker
                return self.load_ref(item_data['$ref'], loader=partial(getattr(self, func.__name__), is_top_level=True, **kwargs))
            else:
                obj = func(self, item_data, path, is_top_level=is_top_level, **kwargs)
                if (support_ref_field):
                    self._resolve_ref(obj, path, **kwargs)
                return obj
        
        def _load_item_ref(self: 'OpenApiParser', path: str, is_top_level: bool = True, **kwargs):
            # noinspection PyTypeChecker
            return self.load_ref(path, loader=partial(getattr(self, func.__name__), is_top_level=is_top_level, **kwargs))
        
        def load_item(self, *args, **kwargs):
            num_args = len(args) + int('path' in kwargs)
            if (num_args == 0 and default_path is not None):
                return _load_item_ref(self, path=default_path)
            elif (num_args == 1):
                return _load_item_ref(self, *args, **kwargs)
            elif (num_args == 2):
                return _load_item(self, *args, **kwargs)
            else:
                raise ValueError(f"Invalid number of positional args passed to loader, expected: 1 or 2, got: {num_args}")
        
        return load_item
    
    if (loader is not None):
        return wrapper(loader)
    else:
        return wrapper

class OpenApiLoader:
    data: Dict[str, Any]
    loaded_objects: Dict[str, Model]
    unresolved_forward_refs: Dict[str, List[ModelClass]]
    id_separator: str = '-'
    
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.loaded_objects = dict()
        self.unresolved_forward_refs = dict()
    
    @classmethod
    def open(cls: Type[T], path: AnyStr, *args, **kwargs) -> T:
        if (isinstance(path, bytes)):
            path = path.decode()
        
        with open(path, 'rt', encoding='utf8') as f:
            if (path.endswith('.json')):
                schema = json.load(f)
            elif (path.endswith('.yaml') or path.endswith('.yml')):
                schema = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported extension: '{''.join(path.rpartition('.')[1:])}'")
        
        return cls(schema, *args, **kwargs)
    
    # region Loader
    def load_data(self, path: str, source: Dict[str, Any] = None, *, base_path: str = None, **kwargs) -> Any:
        if (base_path is None):
            base_path = path
        
        left, sep, right = split_path_left(path)
        if (left == '#'):
            if (not sep):
                return self.data
            else:
                return self.load_data(right, self.data, base_path=base_path, **kwargs)
        
        elif (source is None):
            raise InvalidReferenceFormat(base_path)
        elif (not isinstance(source, dict)):
            raise InvalidReference(base_path)
        elif (left not in source):
            raise UnresolvedReference(base_path)
        elif (not sep):
            return source[left]
        else:
            return self.load_data(right, source[left], base_path=base_path, **kwargs)
    def load_object(self, path: str, source: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        result = self.load_data(path, source, **kwargs)
        if (not isinstance(result, dict)):
            raise InvalidReference(path)
        return result
        
        pass
    def load_ref(self, path: str, *, loader: Callable[[Dict[str, Any], str], M]) -> M:
        if (path in self.loaded_objects):
            return self.loaded_objects[path]
        else:
            return loader(self.load_object(path), path)
    # endregion
    # region Schemas & Classes
    @smart_loader(support_ref_field=False)
    def load_class(self, class_data: Dict[str, Any], path: str, *, is_top_level: bool, force_name: Optional[str] = None, **kwargs) -> ModelClass:
        if (force_name is not None and not is_top_level):
            name = force_name
        else:
            _, _, name = split_path_right(path)
        
        loaded_class = ModelClassImpl.from_dict(class_data)
        loaded_class.name = name
        loaded_class.path = path
        for p, d in loaded_class.properties.items():  # type: str, Dict[str, Any]
            loaded_class.properties[p] = self.load_schema(d, f'{path}/properties/{p}')
        if (isinstance(loaded_class.additional_properties, dict)):
            loaded_class.additional_properties = self.load_schema(loaded_class.additional_properties, f'{path}/additionalProperties')
        
        loaded_class.is_top_level = is_top_level
        loaded_class.pretty_path = name if force_name else None
        return loaded_class
    
    @smart_loader
    def load_schema(self, schema_data: Dict[str, Any], path: str, *, is_top_level: bool, force_name: Optional[str] = None, **kwargs) -> ModelSchema:
        if (force_name is not None and not is_top_level):
            name = force_name
        else:
            _, _, name = split_path_right(path)
        
        field_data = ModelSchemaImpl.from_dict(schema_data)
        field_data.property_name = name
        inheritance_data = InheritanceFilter.from_dict(schema_data)
        if (not inheritance_data.is_empty):
            inheritance_data.all_of = self._load_fields(inheritance_data.all_of, path + '/allOf')
            inheritance_data.any_of = self._load_fields(inheritance_data.any_of, path + '/anyOf')
            inheritance_data.one_of = self._load_fields(inheritance_data.one_of, path + '/oneOf')
            if (inheritance_data.filter_not is not None):
                # noinspection PyTypeChecker
                inheritance_data.filter_not = self.load_schema(inheritance_data.filter_not, path + '/not')
            if (inheritance_data.discriminator is not None):
                if (field_data.property_type is None):
                    field_data.property_type = PropertyType.Object
                elif (field_data.property_type != PropertyType.Object):
                    # ToDo: Discriminator fields could not be used in combination with non-object properties
                    raise ValueError("Discriminator fields could not be used in combination with non-object properties")
        
        if (field_data.property_type is None):
            field_data.cls = Any
        
        elif (field_data.property_type == PropertyType.Integer):
            field_data.cls = int
            field_data.filter = NumericFilter.from_dict(schema_data)
        
        elif (field_data.property_type == PropertyType.Number):
            field_data.cls = float
            field_data.filter = NumericFilter.from_dict(schema_data)
        
        elif (field_data.property_type == PropertyType.String):
            if (DateFormatName.contains_value(field_data.property_format)):
                field_data.cls = datetime
                field_data.filter = DateFilter.from_dict(schema_data)
            else:
                if (field_data.property_format in ('byte', 'binary')):
                    field_data.cls = bytes
                else:
                    field_data.cls = str
                field_data.filter = StringFilter.from_dict(schema_data)
        
        elif (field_data.property_type == PropertyType.Boolean):
            field_data.cls = bool
        
        elif (field_data.property_type == PropertyType.Array):
            if ('items' in schema_data):
                items = self.load_schema(schema_data['items'], path + '/items', force_name=field_data.property_name + self.id_separator + 'item')
                field_data.cls = ListProxy[items.cls]
            else:
                field_data.cls = list
            field_data.filter = ArrayFilter.from_dict(schema_data)
        
        elif (field_data.property_type == PropertyType.Object):
            additional_properties: Union[bool, Dict[str, Any]] = schema_data.get('additionalProperties', True)
            if ('properties' in schema_data):
                field_data.cls = self.load_class(schema_data, path, is_top_level=is_top_level, force_name=field_data.property_name)
            elif (additional_properties == False):
                raise InvalidSchemaFields(path, "'additionalProperties=False' is not allowed in combination with missing 'properties' for 'object' invalid_type")
            elif (isinstance(additional_properties, dict)):
                cls = self.load_schema(additional_properties, path + '/additionalProperties', force_name=field_data.property_name + self.id_separator + 'item')
                field_data.cls = DictProxy[str, cls]
                field_data.filter = DictFilter.from_dict(schema_data)
            else:
                field_data.cls = dict
                field_data.filter = DictFilter.from_dict(schema_data)
        
        field_data.filter = EmptyFilter().mix_with(field_data.filter).mix_with(inheritance_data)
        
        if (inheritance_data.any_of is not None or inheritance_data.one_of is not None):
            if (inheritance_data.all_of is not None):
                raise InvalidSchemaFields(path, f"allOf is not allowed in combination with oneOf/anyOf")
            
            items = Option(inheritance_data.any_of).get_or_else(list()) + Option(inheritance_data.one_of).get_or_else(list())
            field_data.cls = UnionProxy[tuple(items)]
            if (inheritance_data.discriminator is not None):
                field_data.cls = field_data.cls.with_discriminator(inheritance_data.discriminator)
        
        elif (inheritance_data.all_of is not None and field_data.cls == Any):
            field_data.cls, inh_filter = self._merge_classes(inheritance_data.all_of, path, is_top_level=is_top_level, force_name=field_data.property_name)
            inheritance_data = inheritance_data.mix_with(inh_filter)
        
        field_data.filter = field_data.filter.mix_with(inheritance_data)
        if ('enum' in schema_data):
            enum_data = ModelEnumDataImpl.from_dict(schema_data)
            enum_data.name = field_data.property_name
            enum_data.base_class = field_data.cls
            enum_data.path = path + '/enum'
            enum_data.pretty_path = None
            field_data.cls = enum_data
        
        return field_data
    
    def _load_fields(self, f: Optional[List[Dict[str, Any]]], path: str, **kwargs) -> Optional[List[ModelSchema]]:
        if (f is not None):
            return list(self._load_fields_iter(f, path, **kwargs))
        else:
            return None
    def _load_fields_iter(self, f: List[Dict[str, Any]], path: str, **kwargs) -> Iterator[ModelSchema]:
        for i, d in enumerate(f):
            yield self.load_schema(d, f'{path}/.{i}', **kwargs)
    
    def _merge_classes(self, classes: List[ModelSchema], path: str, *, is_top_level: bool, force_name: Optional[str] = None, **kwargs) -> Tuple[ModelClass, Filter]:
        if (force_name is not None):
            name = force_name
        else:
            _, _, name = split_path_right(path)
        
        m = ModelClassImpl(properties={ })
        m.name = name
        m.path = path
        m.is_top_level = is_top_level
        filter = EmptyFilter()
        
        for c in classes:
            filter = filter.mix_with(c.filter)
            
            if (isinstance(c.cls, ModelClass)):
                if (m.additional_properties == True):
                    m.additional_properties = c.cls.additional_properties
                elif (m.type.additional_properties != c.cls.additional_properties):
                    # ToDo: Additional properties conflict error
                    raise ValueError
                
                if (c.cls.is_top_level):
                    m.parents.append(c.cls)
                else:
                    for prop_name, prop_field in c.cls.properties.items():
                        if (prop_name in m.properties and prop_field != m.properties[prop_name]):
                            # ToDo: Field conflict error
                            raise ValueError
                        m.properties[prop_name] = prop_field
                    
                    m.required_properties += c.cls.required_properties
                    if (c.cls.example is not None):
                        m.example = c.cls.example
                    if (c.cls.description is not None):
                        m.example = c.cls.example
                    c.cls.merged = True
            
            else:
                is_generic, tp, args = extract_generic(c.cls)
                if (tp == dict):
                    if (m.additional_properties == False):
                        # ToDo: Additional properties conflict error
                        raise ValueError
                
                elif (tp == Dict):
                    K, V = args
                    if (K == str and isinstance(V, ModelSchema)):
                        if (m.additional_properties == True):
                            m.additional_properties = V
                        elif (m.additional_properties != V):
                            # ToDo: Additional properties conflict error
                            raise ValueError
                
                else:
                    # ToDo: Type error
                    raise ValueError
        
        m.pretty_path = None
        return m, filter
    # endregion
    # region Endpoints
    @smart_loader
    def load_path_item(self, path_item_data: Dict[str, Any], path: str, is_top_level: bool, **kwargs) -> ModelPath:
        _, _, endpoint_path = split_path_right(path)
        path_item = ModelPathImpl.from_dict(path_item_data)
        path_item.endpoint_path = endpoint_path
        path_item.path = path
        path_item.is_top_level = is_top_level
        
        self._load_parameters(path_item.parameters, path + '/parameters')
        for http_method in ALLOWED_HTTP_METHODS:
            if (http_method in path_item_data):
                # noinspection PyTypeChecker
                if (path_item.summary is not None):
                    backup_id = http_method + self.id_separator + path_item.summary.replace(' ', self.id_separator)
                else:
                    backup_id = self._endpoint_name_generator(endpoint_path, http_method=http_method)
                
                path_item.endpoints[http_method] = self.load_endpoint(path_item_data[http_method], path + f'/{http_method}', parent_parameters=path_item.parameters, backup_id=backup_id)
        
        path_item.pretty_path = None
        return path_item
    
    @smart_loader
    def load_endpoint(self, endpoint_data: Dict[str, Any], path: str, *, parent_parameters: List[ModelParameterImpl], backup_id: Optional[str] = None, is_top_level: bool, **kwargs) -> ModelEndpoint:
        endpoint = ModelEndpointImpl.from_dict(endpoint_data)
        endpoint.path = path
        endpoint.is_top_level = True
        
        if (endpoint.operation_id is None):
            if (endpoint.summary is not None):
                endpoint.operation_id = endpoint.summary.replace(' ', self.id_separator)
            else:
                endpoint.operation_id = backup_id
        
        self._load_parameters(endpoint.own_parameters, path + '/parameters')
        params_map = dict()
        for p in parent_parameters:
            params_map[p.name] = p
        for p in endpoint.own_parameters:
            params_map[p.name] = p
        
        endpoint.parent_parameters = parent_parameters
        endpoint.all_parameters = params_map.values()
        
        if (endpoint.request_body is not None):
            endpoint.request_body = self.load_request_body_object(endpoint.request_body, path=path + '/requestBody', operation_id=endpoint.operation_id)
        
        for status in endpoint.responses:
            endpoint.responses[status] = self.load_response_object(endpoint.responses[status], path=path + f'/responses/[{status}]', operation_id=endpoint.operation_id)
        endpoint.default_response = endpoint.responses.pop('default', None)
        
        if (not endpoint.responses):
            # ToDo: Missing required responses
            # raise ValueError
            pass
        
        # ToDo:
        #  - Load Callbacks
        
        endpoint.pretty_path = None
        return endpoint
    
    @smart_loader
    def load_parameter(self, parameter_data: Dict[str, Any], path: str, is_top_level: bool, **kwargs) -> ModelParameter:
        parameter = ModelParameterImpl.from_dict(parameter_data)
        parameter.path = path
        parameter.is_top_level = is_top_level
        
        if (parameter.schema is not None and not isinstance(parameter.schema, ModelSchema)):
            parameter.schema = self.load_schema(parameter.schema, f'{path}/schema', force_name=parameter.name)
        parameter.content = self._load_content(parameter.content, path + '/content', force_name=parameter.name)
        
        parameter.pretty_path = None
        return parameter
    
    @smart_loader
    def load_request_body_object(self, request_body_object_data: Dict[str, Any], path: str, is_top_level: bool, operation_id: str = None, **kwargs) -> ModelRequestBodyObjectImpl:
        _, _, name = split_path_right(path)
        request_body = ModelRequestBodyObjectImpl.from_dict(request_body_object_data)
        request_body.name = name
        request_body.path = path
        request_body.is_top_level = is_top_level
        
        if (operation_id is None):
            operation_id = name
        request_body.content = self._load_content(request_body.content, path + '/content', force_name=operation_id + self.id_separator + 'request', is_top_level=True)
        
        request_body.pretty_path = None
        return request_body
    
    @smart_loader
    def load_response_object(self, response_object_data: Dict[str, Any], path: str, is_top_level: bool, operation_id: Optional[str] = None, **kwargs) -> ModelResponseObject:
        _, _, name = split_path_right(path)
        response = ModelResponseObjectImpl.from_dict(response_object_data)
        response.name = name
        response.path = path
        response.is_top_level = is_top_level
        
        if (operation_id is None):
            operation_id = name
        response.content = self._load_content(response.content, path + '/content', force_name=operation_id + self.id_separator + 'response', is_top_level=True)
        
        response.pretty_path = None
        return response
    
    def _load_content(self, content: Optional[Dict[str, Union[ModelMediaTypeObject, Dict[str, Any]]]], path: str, force_name: str, is_top_level: bool = False) -> Optional[Dict[str, ModelMediaTypeObject]]:
        if (content is None):
            return None
        
        for media_type, media_type_object in content.items():
            if (media_type_object.schema is not None and not isinstance(media_type_object.schema, ModelSchema)):
                # noinspection PyTypeChecker
                media_type_object.schema = self.load_schema(media_type_object.schema, f'{path}/[{media_type}]/schema', force_name=force_name)
                if (is_top_level and isinstance(media_type_object.schema.cls, ModelClass)):
                    media_type_object.schema.cls.is_top_level = True
        
        return content
    
    def _load_parameters(self, params: Iterable[Union[ModelParameter, Dict[str, Any]]], path: str) -> List[ModelParameter]:
        result = self._load_parameters_iter(params, path)
        if (isinstance(params, list)):
            for i, p in enumerate(result):
                params[i] = p
            result = params
        else:
            result = list(result)
        
        return result
    def _load_parameters_iter(self, params: Iterable[Union[ModelParameter, Dict[str, Any]]], path: str) -> Iterator[ModelParameter]:
        for i, p in enumerate(params):
            if (not isinstance(p, ModelParameter)):
                yield self.load_parameter(p, path=path + '/' + p.get('name', f'.{i}'))
    def _endpoint_name_generator(self, endpoint_path: str, *, http_method: Optional[str] = None, version: Optional[str] = None) -> str:
        sep = self.id_separator
        name_split = endpoint_path.strip('/').split('/')
        name_gen = list()
        
        for part in name_split:
            if (part.startswith('{') and part.endswith('}')):
                if (name_gen):
                    name_gen[-1] += f'{sep}by{sep}{part[1:-1]}'
                else:
                    name_gen.append(f'by{sep}{part[1:-1]}')
            elif (re.fullmatch(r'v\d+(?:\.\d+)*', part)):
                if (name_gen):
                    name_gen[-1] += f'{sep}{part}'
                    version = name_gen.pop(-1)
                else:
                    version = part
            else:
                name_gen.append(part)
        
        name = f'{sep}from{sep}'.join(reversed(name_gen))
        if (http_method is not None):
            name = http_method + sep + name
        if (version is not None):
            name += sep * 2 + version
        return name
    # endregion
    # region Meta
    def _resolve_ref(self, loaded_class: Model, path: str, **kwargs):
        if (path in self.unresolved_forward_refs):
            for cls in self.unresolved_forward_refs[path]:
                for f in cls.properties:
                    f.type = loaded_class
            del self.unresolved_forward_refs[path]
        
        self.loaded_objects[path] = loaded_class
    
    @smart_loader
    def load_security_scheme(self, security_scheme_data: Dict[str, Any], path: str, is_top_level: bool, **kwargs) -> ModelSecurityScheme:
        sec_scheme = ModelSecuritySchemeImpl.decode(security_scheme_data)
        sec_scheme.is_top_level = is_top_level
        sec_scheme.path = path
        sec_scheme.name = split_path_right(path)[-1]
        sec_scheme.pretty_path = None
        return sec_scheme
    
    @smart_loader(default_path='#')
    def load_metadata_object(self, metadata_object_data: Dict[str, Any], path: str, **kwargs) -> OpenApiMetadata:
        metadata = OpenApiMetadataImpl.from_dict(metadata_object_data)
        return metadata
    # endregion

class OpenApiParser(OpenApiLoader):
    name: Optional[str]
    author: Optional[str]
    
    metadata: OpenApiMetadata
    path_items: Dict[str, ModelPath]
    security_schemes: Dict[str, ModelSecurityScheme]
    
    # region Top-Level
    def __init__(self, data: Dict[str, Any], name: str = None, *, author: str = None):
        super().__init__(data)
        self.name = name
        self.author = author
        
        self.load_metadata()
        self.path_items = dict()
        self.security_schemes = dict()
    
    def load_all(self):
        self.load_metadata()
        self.load_schemas()
        self.load_path_items()
        self.load_security_schemes()
    def load_metadata(self):
        self.metadata = self.load_metadata_object()
    def load_schemas(self):
        try:
            schemas = self.load_object('#/components/schemas')
        except UnresolvedReference:
            pass
        else:
            for s in schemas:
                self.load_schema(f'#/components/schemas/{s}')
    def load_path_items(self):
        try:
            paths = self.load_object('#/paths')
        except UnresolvedReference as e:
            # ToDo: Missing required field 'path'
            raise ValueError("Missing required field 'path'") from e
        else:
            for p in paths:
                self.path_items[p] = self.load_path_item(f'#/paths/[{p}]')
    def load_security_schemes(self):
        try:
            schemes = self.load_object('#/components/securitySchemes')
        except UnresolvedReference as e:
            pass
        else:
            for s in schemes:
                self.security_schemes[s] = self.load_security_scheme(f'#/components/securitySchemes/[{s}]')
    # endregion


__all__ = \
[
    'OpenApiLoader',
    'OpenApiParser',
]
