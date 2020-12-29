from abc import ABC

from .types import HandlerListType

class IHandlerController(ABC):
    base_path: str
    handlers: HandlerListType
    
    def get_handlers_for(self, host: str) -> HandlerListType:
        pass

__all__ = \
[
    'IHandlerController',
]
