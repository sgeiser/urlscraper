from abc import ABC
from dataclasses import dataclass
from typing import *

from .containers import *
from .monads import *
from .predef import *

class EmptyOption(ValueError):
    pass

T = TypeVar('T')
R = TypeVar('R')
K = TypeVar('K', bound=Monad)
@dataclass(frozen=True, init=False, repr=False)
class Option(Container['Option[T]', T], Monad['Option[T]', T], Functor['Option[T]', T], Generic[T], ABC):
    
    def __new__(cls, value: Optional[T], *, _ignore_selector: bool = False):
        if (_ignore_selector):
            return super().__new__(cls)
        elif (value is None):
            return OptionNone
        else:
            return Some(value)
    
    @classmethod
    def from_optional(cls: Type['Option[T]'], value: Optional[T]) -> 'Option[T]':
        return Option(value)
    
    @classmethod
    def is_option(cls: Type['Option[T]'], value: Any) -> bool:
        """
        Class method which checks if the given value is an `Option`.
        Returns `True` if it is.
        
        Args:
            value: A potential Option to check
        
        Returns:
            `bool`
        
        """
        return isinstance(value, Option)
    
    #region Properties
    @property
    def is_defined(self) -> bool:
        return not self.is_empty
    
    @property
    def non_empty(self) -> bool:
        return self.is_defined
    
    @property
    def get(self) -> T:
        raise NotImplementedError
    
    @property
    def flatten(self) -> T:
        return self.flat_map(identity)
    
    @property
    def as_optional(self) -> Optional[T]:
        raise NotImplementedError
    
    def tuple_transform(self, num_items: int) -> Tuple['Option[T]', ...]:
        raise NotImplementedError
    #endregion
    
    #region Methods
    def get_or_else(self, or_else: T) -> T:
        raise NotImplementedError
    
    def map(self, f: Callable[[T], R]) -> 'Option[R]':
        return self.flat_map(lambda x: Some(f(x)))
    
    def foreach(self, f: Callable[[T], Any]):
        self.map(f)
    #endregion
    
    #region Operators
    def __bool__(self) -> bool:
        return self.is_defined
    
    def __len__(self) -> int:
        return int(self.is_defined)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __iter__(self) -> Iterator[T]:
        raise NotImplementedError
    #endregion

@dataclass(frozen=True, repr=False)
class Some(Option[T], Generic[T]):
    _value: T
    
    def __new__(cls, *args, **kwargs):
        kwargs['_ignore_selector'] = True
        return super().__new__(cls, *args, **kwargs)
    
    #region Properties
    @property
    def is_empty(self):
        return False
    
    @property
    def get(self) -> T:
        return self._value
    
    @property
    def as_optional(self) -> T:
        return self._value
    
    def tuple_transform(self, num_items: int) -> Tuple['Some[T]', ...]:
        return tuple(map(Some, self._value))
    # endregion
    
    # region Methods
    def get_or_else(self, or_else: T) -> T:
        return self._value
    
    def flat_map(self, f: Callable[[T], Option[R]]) -> Option[R]:
        return f(self._value)
    # endregion
    
    # region Operators
    def __repr__(self):
        return f"Some({self._value!r})"
    
    def __iter__(self) -> Iterator[T]:
        yield self._value
    # endregion

@dataclass(frozen=True, repr=False, init=False)
class _OptionNone(Option[T], Generic[T]):
    
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, None, _ignore_selector=True)
    
    # region Properties
    @property
    def is_empty(self):
        return True
    
    @property
    def get(self) -> T:
        raise EmptyOption("Could not get from empty Option")
    
    @property
    def as_optional(self) -> None:
        return None
    
    def tuple_transform(self, num_items: int) -> Tuple['_OptionNone[T]', ...]:
        return tuple([ OptionNone ] * num_items)
    # endregion
    
    # region Methods
    def get_or_else(self, or_else: T) -> T:
        return or_else
    
    def flat_map(self, f: Callable[[T], Option[R]]) -> '_OptionNone[R]':
        # noinspection PyTypeChecker
        return none
    # endregion
    
    # region Operators
    def __repr__(self):
        return f"None"
    
    def __iter__(self):
        return
        # noinspection PyUnreachableCode
        yield
    # endregion

T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')
T4 = TypeVar('T4')
T5 = TypeVar('T5')
T6 = TypeVar('T6')

@overload
def tuple_transform(opt: Option[Tuple[T1]], num_items: int) -> Tuple[Option[T1]]:
    pass
@overload
def tuple_transform(opt: Option[Tuple[T1, T2]], num_items: int) -> Tuple[Option[T1], Option[T2]]:
    pass
@overload
def tuple_transform(opt: Option[Tuple[T1, T2, T3]], num_items: int) -> Tuple[Option[T1], Option[T2], Option[T3]]:
    pass
@overload
def tuple_transform(opt: Option[Tuple[T1, T2, T3, T4]], num_items: int) -> Tuple[Option[T1], Option[T2], Option[T3], Option[T4]]:
    pass
@overload
def tuple_transform(opt: Option[Tuple[T1, T2, T3, T4, T5]], num_items: int) -> Tuple[Option[T1], Option[T2], Option[T3], Option[T4], Option[T5]]:
    pass
@overload
def tuple_transform(opt: Option[Tuple[T1, T2, T3, T4, T5, T6]], num_items: int) -> Tuple[Option[T1], Option[T2], Option[T3], Option[T4], Option[T5], Option[T6]]:
    pass
def tuple_transform(opt: Option[Tuple[T, ...]], num_items: int) -> Tuple[Option[T], ...]:
    return opt.tuple_transform(num_items)

Option.empty = _OptionNone()
OptionNone = Option.empty
none = Option.empty
is_option = Option.is_option

__all__ = \
[
    'EmptyOption',
    'Option',
    'Some',
    'OptionNone',
    'none',
    'is_option',
    'tuple_transform',
]
