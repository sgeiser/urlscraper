from typing import *

from camel_case_switcher import dict_keys_camel_case_to_underscore, dict_keys_underscore_to_camel_case
from dataclasses import is_dataclass
from dataclasses_json import DataClassJsonMixin

from .iencoder import IEncoder, T, EncodedObjType, EncodedObjListType

class DataClassJsonEncoder(IEncoder):
    _type_name = "json dataclass"
    
    @classmethod
    def _is_type(cls, t: Type) -> bool:
        return isinstance(t, type) and issubclass(t, DataClassJsonMixin) and is_dataclass(t)
    
    # noinspection PyMethodOverriding
    @classmethod
    def _decode_single(cls, model: Type[T], obj: EncodedObjType, *, camel_case_switch: bool = False, **kwargs) -> T:
        model: Type[DataClassJsonMixin]
        if (camel_case_switch):
            obj = dict_keys_camel_case_to_underscore(obj, recursive=True)
        return model.from_dict(obj)
    @classmethod
    def _decode_many(cls, model: Type[T], obj: EncodedObjListType, **kwargs) -> List[T]:
        return [ cls._decode_single(model, x, **kwargs) for x in obj ]
    
    # noinspection PyMethodOverriding
    @classmethod
    def _encode_single(cls, model: Type[T], obj: T, *, camel_case_switch: bool = False, **kwargs) -> EncodedObjType:
        model: Type[DataClassJsonMixin]
        result = model.to_dict(obj)
        if (camel_case_switch):
            result = dict_keys_underscore_to_camel_case(result, recursive=True)
        return result
    @classmethod
    def _encode_many(cls, model: Type[T], obj: Iterable[T], **kwargs) -> EncodedObjListType:
        return [ cls._encode_single(model, x, **kwargs) for x in obj ]

__all__ = \
[
    'DataClassJsonEncoder',
]
