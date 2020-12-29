from abc import ABC
from typing import *

from functional import OptionNone, Some, Option

from openapi_parser.model import ModelSchema
from openapi_parser.util.typing_proxy import GenericProxy
from .abstract_writer import Writer

class AttributeWriter(Writer, ABC):
    def parse_attribute(self, name: str, prop: Optional[ModelSchema], *, is_required: bool = True) -> Tuple[str, Option[str], Option[str], Option[str]]:
        field_name_pretty = self.field_name_pretty(name)
        actual_name = self.object_valid_name_filter(field_name_pretty)
        
        if (prop is None):
            f_type = Some('Optional[Any]') if (not is_required) else OptionNone
            f_value = Some('None') if (not is_required) else OptionNone
            f_default = Some('None') if (not is_required) else OptionNone
        
        else:
            if (prop.cls == Any):
                f_type = OptionNone
            else:
                f_type = Some(self.class_name_pretty(prop.cls)) if isinstance(prop, ModelSchema) else OptionNone
            f_default = prop.default
            
            # for enum in find_filters(prop.filter, ModelEnumData):
            #     f_type = Some(self.object_valid_name_filter(self.class_name_pretty(enum)))
            
            if (not is_required):
                f_type = f_type.map('Optional[{}]'.format)
                f_default = f_default or (Some(None) if (not is_required) else OptionNone)
            
            f_value = f_default.map('{!r}'.format)
        
        return actual_name, f_type, f_value, f_default
    
    def join_attribute(self, actual_name: str, f_type: Option[str], f_value: Option[str]) -> str:
        return actual_name + f_type.map(': {}'.format).get_or_else('') + f_value.map(' = {}'.format).get_or_else('')
    
    def extract_generic_coder(self, generic: GenericProxy, coder_type: str) -> Optional[str]:
        parsed = generic.deep_coder(coder_type)
        if (parsed is None):
            return None
        
        return 'lambda x: ' + self._extract_generic_coder('x', *parsed)
    
    def _extract_generic_coder(self, super_var: str, gen: GenericProxy, params: Dict[str, Optional[Union[Tuple, Callable, str, None]]]) -> str:
        items = list()
        for var, coder in params.items():
            if (coder is None):
                coder = var
            elif (isinstance(coder, tuple)):
                coder = Option(self._extract_generic_coder(var, *coder)).map(lambda x: x + f'({var})').get_or_else(var)
            else:
                coder = self.ref_name_pretty(coder)
            
            items.append(coder)
        
        return gen.constructor(f"{gen.item_constructor(tuple(items))} for {', '.join(params.keys())} in {gen.iterator(super_var)}")
    
    def extract_coder(self, prop: ModelSchema, coder_type: str) -> Optional[str]:
        coder = getattr(prop.filter, coder_type)
        if (coder is not None):
            return self.ref_name_pretty(coder)
        elif (isinstance(prop.cls, GenericProxy)):
            return self.extract_generic_coder(prop.cls, coder_type)
        else:
            return None


__all__ = \
[
    'AttributeWriter',
]
