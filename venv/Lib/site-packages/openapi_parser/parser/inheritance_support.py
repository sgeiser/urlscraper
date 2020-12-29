import warnings
from dataclasses import dataclass, field
from functools import reduce
from itertools import chain
from typing import *
from typing import Optional, Dict, List

from dataclasses_json import dataclass_json, LetterCase, DataClassJsonMixin, config
from functional import Option, OptionNone, Some

from openapi_parser.model import Filter, ModelSchema
from openapi_parser.util.utils import mix_options, dict_safe_merge
from .errors import OpenApiLoaderError
from .filters import FilterImpl
from .model_impl import ModelClassImpl


@dataclass(frozen=True)
class UnableToBuildDiscriminator(OpenApiLoaderError):
    filter: 'InheritanceFilter'
    
    @property
    def message(self) -> str:
        return f"Unable to build a discriminator decoder for filter '{self.filter}'"
    
    def __post_init__(self):
        super().__init__(self.message)

@dataclass(frozen=True)
class InvalidAlternativeTypes(UnableToBuildDiscriminator, TypeError):
    filter: 'InheritanceFilter'
    invalid_type: Union[ModelClassImpl, Type]
    
    @property
    def message(self) -> str:
        return f"{super().message}: Only Dict[str, Any] and ModelClass are supported, got: {self.invalid_type}"
    
    def __post_init__(self):
        super().__init__(self.message)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DiscriminatorObject(DataClassJsonMixin):
    property_name: str
    mapping: Optional[Dict[str, str]] = None
    
    def mix_with(self, other: 'DiscriminatorObject') -> 'DiscriminatorObject':
        if (self.property_name != other.property_name):
            # ToDo: Different discriminator data
            raise ValueError
        
        return DiscriminatorObject \
        (
            property_name = self.property_name,
            mapping = mix_options(self.mapping, other.mapping).map(dict_safe_merge).as_optional,
        )
    
    def decoder(self, items: List[ModelSchema]) -> Optional[str]:
        mapping = Option(self.mapping).get_or_else({ get_class_name(it.cls): get_class_name(it.cls) for it in items })
        if (len(mapping) < 2):
            return None
        
        return f"discriminator_decoder(discriminator_key={self.property_name!r}, mappings={{ {', '.join(f'{k!r}: {v}' for k, v in mapping.items())} }})"

T = TypeVar('T')
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InheritanceFilter(FilterImpl[T], Generic[T]):
    discriminator: Optional[DiscriminatorObject] = None
    all_of: Optional[List[ModelSchema]] = None
    any_of: Optional[List[ModelSchema]] = None
    one_of: Optional[List[ModelSchema]] = None
    filter_not: Optional[ModelSchema] = field(default=None, metadata=config(field_name='not'))
    
    def check_value(self, value: T):
        warnings.warn(RuntimeWarning("InheritanceFilter is not implemented"))
        return True
    
    @property
    def decoder(self):
        if (self.discriminator is None):
            return None
        
        items = Option(self.any_of).get_or_else(list()) + Option(self.one_of).get_or_else(list()) + Option(self.all_of).get_or_else(list())
        for it in items:
            if (it.cls != dict and not isinstance(it.cls, ModelClassImpl)):
                raise InvalidAlternativeTypes(self, it.cls)
        
        return self.discriminator.decoder(items)
    
    def mix_with(self, f: Filter[T]) -> Filter[T]:
        if (isinstance(f, InheritanceFilter)):
            filter_not = mix_options(self.filter_not, f.filter_not)
            filter_all_mixin = OptionNone
            if (filter_not.non_empty):
                if (len(filter_not.get) > 1):
                    filter_not = OptionNone
                    filter_all_mixin = Some([])
                    # ToDo: Mix
                    raise NotImplementedError("Mixing of multiple NOT is not currently supported")
            
            return InheritanceFilter \
            (
                discriminator = mix_options(self.discriminator, f.discriminator).map(lambda lst: reduce(DiscriminatorObject.mix_with, lst)).as_optional,
                all_of        = mix_options(self.all_of, f.all_of, filter_all_mixin).map(chain.from_iterable).map(list).as_optional,
                any_of        = mix_options(self.any_of, f.any_of).map(chain.from_iterable).map(list).as_optional,
                one_of        = mix_options(self.one_of, f.one_of).map(chain.from_iterable).map(list).as_optional,
                filter_not    = filter_not.as_optional,
            )
        
        else:
            return super(InheritanceFilter, self).mix_with(f)

def get_class_name(t: Union[Type, ModelClassImpl]) -> str:
    if (isinstance(t, ModelClassImpl)):
        return t.name
    else:
        return t.__name__
del T

T = TypeVar('T', bound=DataClassJsonMixin)
class DiscriminatorDecoderError(ValueError):
    pass
class UnregisteredDiscriminatorTypeError(DiscriminatorDecoderError):
    pass

def discriminator_decoder(discriminator_key: str, mappings: Dict[str, Type[T]], *, default_factory: Union[Callable[[], T], Type[T]] = None) -> Callable[[Dict[str, Any]], T]:
    lst_gen = lambda: ', '.join(f"'{t}'" for t in mappings.keys())
    def decoder(data: Dict[str, Any]) -> T:
        if (not isinstance(data, dict)):
            raise DiscriminatorDecoderError(f"A dict-like object is expected to decode any of [ {lst_gen()} ], got {type(data)}")
        elif (discriminator_key not in data):
            raise DiscriminatorDecoderError(f"Discriminator field '{discriminator_key}' was not presented in the body: '{data}'")
        elif (data[discriminator_key] not in mappings):
            raise UnregisteredDiscriminatorTypeError(f"Discriminator field '{discriminator_key}' has invalid value '{data[discriminator_key]}'")
        else:
            return mappings[data[discriminator_key]].from_dict(data)
    
    if (default_factory is not None):
        def safe_decoder(data: Dict[str, Any]) -> Optional[T]:
            try:
                return decoder(data)
            except DiscriminatorDecoderError:
                if (isinstance(default_factory, type) and issubclass(default_factory, DataClassJsonMixin)):
                    return default_factory.from_dict(data)
                else:
                    return default_factory()
        result = safe_decoder
    
    else:
        result = decoder
    
    return result

__all__ = \
[
    'DiscriminatorDecoderError',
    'DiscriminatorObject',
    'InheritanceFilter',
    'InvalidAlternativeTypes',
    'UnableToBuildDiscriminator',
    'UnregisteredDiscriminatorTypeError',
    
    'discriminator_decoder',
]
