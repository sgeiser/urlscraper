from abc import ABC
from typing import *

from http_server_base.logged_request_handler import Logged_RequestHandler
from http_server_base.tools.types import JsonSerializable
from .extras import CanonicalArgumentListType

class IRest_RequestHandler(Logged_RequestHandler, ABC):
    base_path: str

    def get_argument_value(self, param_name: str, param_types: Tuple[Type], param_default, required: bool, source: dict, source_type: str, support_capitalization_style_switch: bool) -> Any:
        pass
    def parse_body_args(self):
        pass
    def get_args(self, source: dict, args_description: CanonicalArgumentListType, source_type: str, support_capitalization_style_switch: bool):
        pass
    def invalid_body_handler(self, content_type):
        pass
    
    T = TypeVar('T')
    RespondableType = Union[JsonSerializable, bytes]
    def resp_paging(self,
            result_keys: List[T], result_values: Union[List[Union[JsonSerializable, bytes]], Callable[[T], Union[JsonSerializable, bytes]]],
            page: int = None, per_page: int = None, *,
            arg_name_page: str = 'page', arg_name_per_page: str = 'per_page', result_name='results',
            code: int = 200, message=None, url_template=None,
    ):
        pass

__all__ = \
[
    'IRest_RequestHandler',
]
