from functools import partial
from typing import *

from dataclasses_json import DataClassJsonMixin
from functional import Some

from openapi_parser.model import ModelClass, ModelSchema, HavingPath, HavingExtendedDescription, ModelEnumData
from openapi_parser.util.utils import StrIO
from .abstract_writer import Writer, yielder, writer
from .attribute_writer import AttributeWriter
from .description_writer import DescriptionWriter
from .footer_writer import Exporting

class ClassWriter(Exporting, AttributeWriter, DescriptionWriter, Writer):
    def dump_class_description(self, cls: HavingExtendedDescription, *, path_cls: Optional[HavingPath] = None, cls_all_required_properties: List[str] = None, compact: bool = False) -> Iterator[str]:
        if (cls_all_required_properties is None):
            if (isinstance(cls, ModelClass)):
                cls_all_required_properties = cls.all_required_properties
            else:
                cls_all_required_properties = list()
        
        gen = partial(self.generate_class_description, cls, path_cls=path_cls, cls_all_required_properties=cls_all_required_properties)
        yield from self.smart_description(gen, compact=compact)
    
    def generate_class_description(self, cls: HavingExtendedDescription, *, path_cls: Optional[HavingPath] = None, cls_all_required_properties: Optional[List[str]], compact: bool):
        def extra_gen():
            if (cls_all_required_properties):
                yield "Required Properties:"
                yield from (f" - {self.object_valid_name_filter(self.field_name_pretty(f_name))}" for f_name in cls_all_required_properties)
                if (not compact):
                    yield
        
        yield from self.generate_item_description(item=cls, path_item=path_cls, item_type='class', compact=compact, extra_gen=extra_gen())
    
    def dump_enum(self, schema: ModelSchema, enum_data: ModelEnumData) -> Iterator[str]:
        cls_name = self.object_valid_name_filter(self.class_name_pretty(enum_data))
        
        self.export(cls_name)
        yield f'class {cls_name}(Enum):'
        with self.indent():
            yield from self.dump_class_description(schema, path_cls=enum_data)
            yield from map(lambda v: f'{self.object_valid_name_filter(self.enum_entry_name_pretty(v))} = {v!r}', enum_data.possible_values)
        yield
    
    def dump_property(self, name: str, prop: ModelSchema, *, only_if_has_default: Optional[bool] = None, is_required: bool = True) -> Iterator[str]:
        actual_name, f_type, f_value, f_default = self.parse_attribute(name, prop, is_required=is_required)
        
        if (only_if_has_default is not None and f_default.is_empty == only_if_has_default):
            return
        
        f_constructor = dict()
        f_constructor_meta = dict()
        encoder = self.extract_coder(prop, 'encoder')
        if (encoder is not None):
            f_constructor_meta['encoder'] = encoder
        decoder = self.extract_coder(prop, 'decoder')
        if (decoder is not None):
            f_constructor_meta['decoder'] = decoder
        if (actual_name != self.field_name_pretty(name)):
            f_constructor_meta['field_name'] = '{!r}'.format(name)
        
        if (f_constructor_meta):
            f_constructor['metadata'] = self.constructor('config', **f_constructor_meta)
        if (prop.default.non_empty and isinstance(prop.default.get, (list, dict, set, tuple))):
            if (f_default.get):
                f_constructor['default_factory'] = f'lambda: {prop.default.get!r}'
            else:
                f_constructor['default_factory'] = type(prop.default.get).__name__
        if (f_constructor):
            if (f_default.non_empty):
                if ('default_factory' not in f_constructor):
                    f_constructor['default'] = '{!r}'.format(f_default.get)
            f_value = Some(self.constructor('field', **f_constructor))
        else:
            f_value = f_default.map('{!r}'.format)
        
        yield self.join_attribute(actual_name, f_type, f_value)
        yield from self.dump_class_description(prop, compact=True)
    
    def dump_class(self, cls: ModelClass) -> Tuple[List[str], Iterator[str]]:
        cls_name = self.object_valid_name_filter(self.class_name_pretty(cls))
        cls_all_req_properties = cls.all_required_properties
        
        dataclass_json_config = dict()
        dataclass_json_config['letter_case'] = 'LetterCase.CAMEL'
        self.export(cls_name)
        yield self.constructor('@dataclass_json', **dataclass_json_config)
        yield '@dataclass'
        yield f"class {cls_name}({', '.join(self.object_valid_name_filter(self.class_name_pretty(p)) for p in (cls.parents + [ DataClassJsonMixin ]))}):"
        
        with self.indent():
            yield from self.dump_class_description(cls, cls_all_required_properties=cls_all_req_properties)
            for f_name, f_data in cls.all_properties_iter:
                yield from self.dump_property(f_name, f_data, only_if_has_default=False, is_required=f_name in cls_all_req_properties)
            for f_name, f_data in cls.all_properties_iter:
                yield from self.dump_property(f_name, f_data, only_if_has_default=True, is_required=f_name in cls_all_req_properties)
        
        yield
    
    # region Writers
    @yielder
    def yield_class(self, cls: ModelClass) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_class(cls)
    
    @overload
    def write_class(self, cls: ModelClass) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_class(self, cls: ModelClass, *, file: StrIO) -> None:
        pass
    @writer
    def write_class(self, cls: ModelClass) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_class(cls)
    # endregion


__all__ = \
[
    'ClassWriter',
]
