from abc import ABC
from functools import partial
from typing import *

import http_server_base.tools.inspect_tools as IT
from .encoder_error import EncoderError

EncodedObjType = Dict[str, Any]
EncodedObjListType = List[EncodedObjType]
T = TypeVar('T')
class IEncoder(Generic[T], ABC):
    _type_name: str = "appropriate type"
    _errors: Tuple[Type[Exception], ...] = (TypeError, KeyError, ValueError, AttributeError)
    
    @classmethod
    def bind(cls, **params) -> 'IEncoder[T]':
        instance = cls()
        
        instance.encode_single = partial(instance.encode_single, **params)
        instance.encode_many   = partial(instance.encode_many,   **params)
        instance.encode_smart  = partial(instance.encode_smart,  **params)
        
        instance.decode_single = partial(instance.decode_single, **params)
        instance.decode_many   = partial(instance.decode_many,   **params)
        instance.decode_smart  = partial(instance.decode_smart,  **params)
        
        return instance
    
    @classmethod
    def _is_type(cls, t: Type) -> bool:
        raise NotImplementedError
    @classmethod
    def _check_type(cls, t: Type):
        if (not cls._is_type(t)):
            raise TypeError(f"Type '{t}' is not a {cls._type_name}")
    @classmethod
    def _is_many(cls, t: Type) -> bool:
        return IT.is_list_type(t)
    @classmethod
    def _unwrap_many(cls, t: Type[List[T]]) -> Type[T]:
        return IT.unfold_list_type(t)
    
    @classmethod
    def _decode_single(cls, model: Type[T], obj: EncodedObjType, **kwargs) -> T:
        raise NotImplementedError
    @classmethod
    def decode_single(cls, model: Type[T], obj: EncodedObjType, **kwargs) -> T:
        cls._check_type(model)
        try:
            return cls._decode_single(model, obj, **kwargs)
        except cls._errors as e:
            raise EncoderError(f"Cannot parse model '{model.__name__}' from '{obj}': {e}") from e
    @classmethod
    def _decode_many(cls, model: Type[T], obj: EncodedObjListType, **kwargs) -> List[T]:
        raise NotImplementedError
    @classmethod
    def decode_many(cls, model: Type[T], obj: EncodedObjListType, **kwargs) -> List[T]:
        cls._check_type(model)
        try:
            return cls._decode_many(model, obj, **kwargs)
        except cls._errors as e:
            raise EncoderError(f"Cannot parse model '{model.__name__}' from '{obj}': {e}") from e
    
    @classmethod
    @overload
    def decode_smart(cls, model: Type[T], obj: EncodedObjType, **kwargs) -> T:
        pass
    @classmethod
    @overload
    def decode_smart(cls, model: Type[List[T]], obj: EncodedObjListType, **kwargs) -> List[T]:
        pass
    @classmethod
    def decode_smart(cls, model: Union[Type[T], Type[List[T]]], obj: Union[EncodedObjType, EncodedObjListType], **kwargs) -> Union[T, List[T]]:
        if (cls._is_many(model)):
            tp = cls._unwrap_many(model)
            func = cls.decode_many
        else:
            tp = model
            func = cls.decode_single
        return func(tp, obj, **kwargs)
    
    @classmethod
    def _encode_single(cls, model: Type[T], obj: T, **kwargs) -> EncodedObjType:
        raise NotImplementedError
    @classmethod
    def encode_single(cls, model: Type[T], obj: T, **kwargs) -> EncodedObjType:
        cls._check_type(model)
        return cls._encode_single(model, obj, **kwargs)
    @classmethod
    def _encode_many(cls, model: Type[T], obj: Iterable[T], **kwargs) -> EncodedObjListType:
        raise NotImplementedError
    @classmethod
    def encode_many(cls, model: Type[T], obj: Iterable[T], **kwargs) -> EncodedObjListType:
        cls._check_type(model)
        return cls._encode_many(model, obj, **kwargs)
    
    @classmethod
    @overload
    def encode_smart(cls, model: Type[T], obj: T, **kwargs) -> EncodedObjType:
        pass
    @classmethod
    @overload
    def encode_smart(cls, model: Type[List[T]], obj: List[T], **kwargs) -> EncodedObjListType:
        pass
    @classmethod
    def encode_smart(cls, model: Union[Type[T], Type[List[T]]], obj: Union[T, List[T]], **kwargs) -> Union[EncodedObjType, EncodedObjListType]:
        if (cls._is_many(model)):
            tp = cls._unwrap_many(model)
            func = cls.encode_many
        else:
            tp = model
            func = cls.encode_single
        return func(tp, obj, **kwargs)

__all__ = \
[
    'EncodedObjType',
    'EncodedObjListType',
    'IEncoder',
]
__pdoc_extras__ = \
[
    'EncodedObjType',
    'EncodedObjListType',
]
