from typing import *

from http_server_base.tools import dict_filter_out
from .dataclass_json_encoder import DataClassJsonEncoder
from .iencoder import EncodedObjType

T = TypeVar('T')
class FilteringJsonEncoder(DataClassJsonEncoder):
    @classmethod
    def _encode_single(cls, model: Type[T], obj: T, **kwargs) -> EncodedObjType:
        result = super()._encode_single(model, obj, **kwargs)
        result = dict_filter_out(result)
        return result

__all__ = \
[
    'FilteringJsonEncoder',
]
