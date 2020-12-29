import datetime
import re
from abc import ABC
from dataclasses import dataclass, field, replace
from functools import reduce
from operator import mul
from typing import *

from dataclasses_json import dataclass_json, LetterCase, config, DataClassJsonMixin
from functional import Option
from typing.re import *

from openapi_parser.model import Filter
from openapi_parser.util.typing_proxy import ref_name_pretty
from openapi_parser.util.utils import mix_options, combine_regular_expressions
from .date_formats import *
from .errors import *

@dataclass(frozen=True)
class UnableToConstructCoder(OpenApiLoaderError):
    filter: 'Filter'
    comment: Optional[str] = None
    @property
    def message(self) -> str:
        msg = f"Unable to construct encoder/decoder for filter '{self.filter}'"
        if (self.comment is not None):
            msg += ': ' + self.comment
        else:
            msg += '.'
        return msg
    
    def __post_init__(self):
        super().__init__(self.message)


T = TypeVar('T')
Z = TypeVar('Z')
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class FilterImpl(Filter, DataClassJsonMixin, Generic[T], ABC):
    
    def __init__(self, *args, **kwargs):
        pass
    
    def check_value(self, value: T) -> bool:
        raise NotImplementedError
    
    @property
    def decoder(self) -> Optional[Callable[[Z], T]]:
        return None
    @property
    def encoder(self) -> Optional[Callable[[T], Z]]:
        return None
    def decode(self, value: Z) -> T:
        if (self.decoder is None):
            return value
        else:
            return self.decoder(value)
    def encode(self, value: T) -> Z:
        if (self.encoder is None):
            return value
        else:
            return self.encoder(value)
    
    @classmethod
    def empty(cls) -> Optional['Filter[T]']:
        return cls()
    
    @property
    def is_empty(self) -> bool:
        return self == self.empty()
    
    def mix_with(self, f: 'Filter[T]') -> 'Filter[T]':
        if (f.is_empty):
            return self
        elif (self.is_empty):
            return f
        else:
            return MultiFilter([ self, f ])

@dataclass
class MultiFilter(FilterImpl[T], Generic[T]):
    filters: List[Filter[T]]
    def check_value(self, value: T):
        return all(f.check_value(value) for f in self.filters)
    
    @classmethod
    def empty(cls) -> None:
        return None
    
    def mix_with(self, f: Filter[T]) -> 'MultiFilter[T]':
        return replace(self, filters=[ *self.filters, f ])
    
    @property
    def decoder(self) -> Optional[Callable[[Z], T]]:
        non_empty_decoders = list(filter(None, map(lambda f: f.decoder, self.filters)))
        if (len(non_empty_decoders) > 1):
            raise UnableToConstructCoder(self)
        elif (len(non_empty_decoders) == 1):
            return non_empty_decoders[0]
        else:
            return None
    
    @property
    def encoder(self) -> Optional[Callable[[T], Z]]:
        non_empty_encoders = list(filter(None, map(lambda f: f.decoder, self.filters)))
        if (len(non_empty_encoders) > 1):
            raise UnableToConstructCoder(self)
        elif (len(non_empty_encoders) == 1):
            return non_empty_encoders[0]
        else:
            return None
del Z

@dataclass
class EmptyFilter(FilterImpl[T], Generic[T]):
    def check_value(self, value: T) -> bool:
        return True

N = TypeVar('N', int, float)
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NumericFilter(FilterImpl[N], Generic[N]):
    maximum: Optional[N] = None
    minimum: Optional[N] = None
    exclusive_maximum: Optional[N] = None
    exclusive_minimum: Optional[N] = None
    multiple_of: Optional[int] = None
    
    def check_value(self, value: N) -> bool:
        return \
            (self.maximum is None           or value <= self.maximum) and \
            (self.minimum is None           or value >= self.minimum) and \
            (self.exclusive_maximum is None or value < self.exclusive_maximum) and \
            (self.exclusive_minimum is None or value > self.exclusive_minimum) and \
            (self.multiple_of is None       or value % self.multiple_of == 0)
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (isinstance(f, NumericFilter)):
            return NumericFilter \
            (
                maximum           = mix_options(self.maximum, f.maximum).map(min).as_optional,
                exclusive_maximum = mix_options(self.exclusive_maximum, f.exclusive_maximum).map(min).as_optional,
                minimum           = mix_options(self.minimum, f.minimum).map(max).as_optional,
                exclusive_minimum = mix_options(self.exclusive_minimum, f.exclusive_minimum).map(max).as_optional,
                multiple_of       = mix_options(self.multiple_of, f.multiple_of).map(lambda lst: reduce(mul, lst, 1)).as_optional,
            )
        else:
            return super().mix_with(f)
del N

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StringFilter(FilterImpl[AnyStr], Generic[AnyStr]):
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    pattern: Optional[Pattern[AnyStr]] = field(default=None, metadata=config(decoder=lambda s: Option(s).map(re.compile).as_optional, encoder=lambda x: Option(x).map(lambda r: r.pattern).get_or_else(None)))
    
    def check_value(self, value: AnyStr) -> bool:
        return \
            (self.max_length is None or self.max_length >= len(value)) and \
            (self.min_length is None or self.min_length <= len(value)) and \
            (self.pattern is None or self.pattern.search(value))
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (isinstance(f, StringFilter)):
            return StringFilter \
            (
                max_length = mix_options(self.max_length, f.max_length).map(min).as_optional,
                min_length = mix_options(self.min_length, f.min_length).map(max).as_optional,
                pattern    = mix_options(self.pattern, f.pattern).map(combine_regular_expressions).as_optional,
            )
        else:
            return super().mix_with(f)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ArrayFilter(FilterImpl[List[T]], Generic[T]):
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    unique_items: bool = False
    
    def check_value(self, value: List[T]) -> bool:
        return \
            (self.max_items is None or self.max_items >= len(value)) and \
            (self.min_items is None or self.min_items <= len(value)) and \
            (not self.unique_items or len(set(value)) == len(value))
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (isinstance(f, ArrayFilter)):
            return ArrayFilter \
            (
                max_items    = mix_options(self.max_items, f.max_items).map(min).as_optional,
                min_items    = mix_options(self.min_items, f.min_items).map(max).as_optional,
                unique_items = self.unique_items or f.unique_items,
            )
        else:
            return super().mix_with(f)

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DictFilter(FilterImpl[Dict[str, T]], Generic[T]):
    max_properties: Optional[int] = None
    min_properties: Optional[int] = None
    
    def check_value(self, value: T) -> bool:
        return \
            (self.max_properties is None or self.max_properties >= len(value)) and \
            (self.min_properties is None or self.min_properties <= len(value))
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (isinstance(f, DictFilter)):
            return DictFilter \
            (
                max_properties = mix_options(self.max_properties, f.max_properties).map(min).as_optional,
                min_properties = mix_options(self.min_properties, f.min_properties).map(max).as_optional,
            )
        else:
            return super().mix_with(f)

D = TypeVar('D', datetime.datetime, datetime.date, datetime.time)
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DateFilter(FilterImpl[str], Generic[D]):
    format: DateFormatName
    
    @property
    def cls(self) -> Type[D]:
        return DateFormatType[self.format.name].value
    
    def check_value(self, value: str) -> bool:
        try:
            self.decode(value)
        except ValueError:
            return False
        else:
            return True
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (self == f):
            return self
        elif (isinstance(f, DateFilter)):
            # ToDo: Mixing conflict error
            raise ValueError
        else:
            return super().mix_with(f)
    
    @property
    def decoder(self) -> Union[str, Callable[[D], str]]:
        if (type(self.cls) == datetime.date):
            return self.cls.isoformat
        else:
            _, _, cls_name = ref_name_pretty(self.cls).rpartition('.')
            return f'datetime_decoder({cls_name})'
    @property
    def encoder(self) -> Callable[[D], str]:
        return self.cls.isoformat
    
    @classmethod
    def empty(cls) -> None:
        return None

DT = TypeVar('DT', datetime.date, datetime.time, datetime.datetime)
def datetime_decoder(cls: Type[DT]) -> Callable[[str], DT]:
    def decoder(s: str) -> DT:
        if (not isinstance(s, str)):
            raise ValueError(f"Unable to decode {cls.__name__}: expected str, got '{s}' ({type(s)})")
        return cls.fromisoformat(s.replace('Z', '+00:00'))
    return decoder
del DT

def find_filters(f: Filter, t: Type[T]) -> Iterator[T]:
    """
    Finds the filter of the given type.
    Could result in more than one filter if `MultiFilter` was used.

    Arguments:
        f: `Filter` instance to search from

        t: `Type[T]`. Type of the filter to search for

    Returns:
        `Iterator[T]`: Iterator for the matched filters
    """
    
    if (not f.is_empty):
        if (isinstance(f, t)):
            yield f
        elif (isinstance(f, MultiFilter)):
            for z in f.filters:
                yield from find_filters(z, t)


__all__ = \
[
    'ArrayFilter',
    'DateFilter',
    'DictFilter',
    'EmptyFilter',
    'FilterImpl',
    'MultiFilter',
    'NumericFilter',
    'StringFilter',
    
    'UnableToConstructCoder',
    'datetime_decoder',
    'find_filters',
]
