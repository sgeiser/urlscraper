from abc import ABC
from typing import *

from dataclasses import dataclass, field

from .extras import CanonicalArgumentListType

T = TypeVar('T')
@dataclass
class Endpoint(Generic[T], ABC):
    name: str
    method: str
    key: T
    path: str
    paths: Tuple[str, T]
    
    matches: Callable[[str], bool] = field(repr=False)
    
    query_arguments: CanonicalArgumentListType
    body_arguments: CanonicalArgumentListType
    path_arguments: CanonicalArgumentListType
    header_arguments: CanonicalArgumentListType
    arguments: Dict[str, CanonicalArgumentListType] = field(init=False)
    
    action: Callable[[Any], Awaitable[Any]] = field(repr=False, default=None)
    extra_args: Dict[str, Any] = field(repr=False, default_factory=dict)
    
    def __post_init__(self):
        self.arguments = { s: getattr(self, f'{s}_arguments') for s in self.arguments_sources }
    
    @property
    def arguments_sources(self) -> List[str]:
        return [ 'query', 'body', 'path', 'header' ]

__all__ = \
[
    'Endpoint',
]
