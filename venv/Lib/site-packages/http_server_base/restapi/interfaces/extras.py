from typing import *

# Argument type is either:
#  - str: name
#  - tuple: (name)
#  - tuple: (name, type)
#  - tuple: (name, type, default)
# Type also might be a tuple of types
# For 'Any' type, use object or None
ArgumentType = Union \
[
    str,
    Tuple[str],
    Tuple[str, Union[Type, Tuple[Type], Set[Any]]],
    Tuple[str, Union[Type, Tuple[Type], Set[Any]], Any],
]
ArgumentListType = Optional[List[ArgumentType]]
CanonicalArgumentType = Tuple[str, Union[Tuple[Optional[Type], ...], Set[Any]], Any, bool]
CanonicalArgumentListType = List[CanonicalArgumentType]

# func(method: str, path: str, base_path: str = '') -> path, action
MapperFuncType = Callable[[str, str, str], Tuple[str, Callable]]

DEFAULT_ALLOWED_METHODS = [ 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD' ]

class ArgumentError(Exception):
    pass
class ArgumentValueError(ArgumentError, ValueError):
    pass
class ArgumentTypeError(ArgumentError, TypeError):
    pass

class MethodNotAllowedError(Exception):
    pass

__all__ = \
[
    # Constants
    'DEFAULT_ALLOWED_METHODS',
    
    # Type Aliases
    'ArgumentListType',
    'ArgumentType',
    'CanonicalArgumentListType',
    'CanonicalArgumentType',
    'MapperFuncType',
    
    # Errors
    'ArgumentError',
    'ArgumentTypeError',
    'ArgumentValueError',
    'MethodNotAllowedError'
]
__pdoc_extras__ = \
[
    'DEFAULT_ALLOWED_METHODS',
    
    'ArgumentListType',
    'ArgumentType',
    'CanonicalArgumentListType',
    'CanonicalArgumentType',
    'MapperFuncType',
]
