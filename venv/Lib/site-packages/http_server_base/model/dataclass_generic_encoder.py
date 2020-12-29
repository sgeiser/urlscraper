from typing import *

from dataclasses import is_dataclass
from dataclasses_json import DataClassJsonMixin, dataclass_json

from .dataclass_json_encoder import DataClassJsonEncoder
from .iencoder import EncodedObjType, EncodedObjListType

T = TypeVar('T')
class DataClassGenericEncoder(DataClassJsonEncoder):
    _type_name = "dataclass"
    _cache: Dict[Type[T], Type[DataClassJsonMixin]] = dict()
    
    @classmethod
    def _is_type(cls, t: Type[T]) -> bool:
        return isinstance(t, type) and is_dataclass(t)
    @classmethod
    def _is_json_dataclass(cls, t: Type[T]) -> bool:
        return issubclass(t, DataClassJsonMixin)
    @classmethod
    def _get_json_dataclass(cls, t: Type[T]) -> Type[DataClassJsonMixin]:
        if (cls._is_json_dataclass(t)):
            return t
        elif (t in cls._cache):
            return cls._cache[t]
        else:
            json_dc = dataclass_json(t)
            cls._cache[t] = json_dc
            return json_dc
    
    # noinspection PyMethodOverriding
    @classmethod
    def _decode_single(cls, model: Type[T], obj: EncodedObjType, **kwargs) -> T:
        model = cls._get_json_dataclass(model)
        return super()._decode_single(model, obj, **kwargs)
    @classmethod
    def _decode_many(cls, model: Type[T], obj: EncodedObjListType, **kwargs) -> List[T]:
        model = cls._get_json_dataclass(model)
        return super()._decode_many(model, obj, **kwargs)
    
    # noinspection PyMethodOverriding
    @classmethod
    def _encode_single(cls, model: Type[T], obj: T, **kwargs) -> EncodedObjType:
        model = cls._get_json_dataclass(model)
        return super()._encode_single(model, obj, **kwargs)
    @classmethod
    def _encode_many(cls, model: Type[T], obj: Iterable[T], **kwargs) -> EncodedObjListType:
        model = cls._get_json_dataclass(model)
        return super()._encode_many(model, obj, **kwargs)

__all__ = \
[
    'DataClassGenericEncoder',
]
