from abc import ABC
from dataclasses import dataclass, field, replace
from typing import *
# noinspection PyUnresolvedReferences, PyProtectedMember
from typing import _SpecialForm

from typing_inspect import get_origin, is_generic_type, get_args

from openapi_parser.model import Model, ModelClass, HavingPath, ModelSchema
from .naming_conventions import *

@dataclass(repr=False, frozen=True)
class GenericProxy(ABC):
    args: Tuple[Union[Model, Type, None], ...]
    _base_class: _SpecialForm = field(init=False, repr=False, compare=False, hash=False)
    
    @property
    def base(self) -> _SpecialForm:
        return self._base_class
    @property
    def __name__(self) -> str:
        # noinspection PyProtectedMember,PyUnresolvedReferences
        return self.base._name
    
    def __repr__(self):
        return generic_repr(self.base, self.args)
    
    def constructor(self, data: str) -> Optional[str]:
        raise NotImplementedError
    @classmethod
    def item_constructor(cls, items: Tuple[str, ...]) -> Optional[str]:
        raise NotImplementedError
    @classmethod
    def iterator(cls, data: str) -> Optional[str]:
        raise NotImplementedError
    
    def deep_coder(self, coder_type: str) -> Optional[Tuple['GenericProxy', Dict[str, Union[Tuple, Callable, str, None]]]]:
        """
        Returns a tuple of 3 thins:
         - GenericProxy class
         - Mapping of var name to either coder or deep_coder result
        """
        
        def _requires(generic: GenericProxy):
            for arg in generic.args:
                if (isinstance(arg, GenericProxy)):
                    if (_requires(arg)):
                        return True
                elif (isinstance(arg, ModelSchema) and not arg.filter.is_empty):
                    return getattr(arg.filter, coder_type) is not None
        
        if (not _requires(self)):
            return None
        
        var = 0
        def _gen(generic: GenericProxy):
            nonlocal var
            params = dict()
            for arg in generic.args:
                var += 1
                if (isinstance(arg, ModelSchema) and not arg.filter.is_empty):
                    coder = getattr(arg.filter, coder_type, None)
                elif (isinstance(arg, GenericProxy)):
                    coder = _gen(arg)
                else:
                    coder = None
                params[f'_{var}'] = coder
            
            return generic, params
        
        return _gen(self)

@dataclass(repr=False, frozen=True)
class _UnionProxy(GenericProxy):
    args: Tuple[Union[Model, Type, None], ...]
    _base_class = Union
    
    discriminator: Any = field(default=None)
    
    def constructor(self, data: str) -> None:
        from openapi_parser.parser.inheritance_support import DiscriminatorObject
        d: DiscriminatorObject = self.discriminator
        if (d is None):
            return None
        else:
            # noinspection PyTypeChecker
            return d.decoder(list(self.args))
    
    @classmethod
    def item_constructor(cls, data: Tuple[str, ...]) -> None:
        return None
    @classmethod
    def iterator(cls, data: str) -> None:
        return None
    
    def with_discriminator(self, discriminator) -> '_UnionProxy':
        return replace(self, discriminator=discriminator)

@dataclass(repr=False, frozen=True)
class _ListProxy(GenericProxy):
    args: Tuple[Union[ModelSchema, Type]]
    _base_class = List
    
    @property
    def arg(self):
        return self.args[0]
    
    def constructor(self, data: str) -> str:
        return f'[ {data} ]'
    @classmethod
    def item_constructor(cls, data: Tuple[str]) -> str:
        return data[0]
    @classmethod
    def iterator(cls, data: str) -> str:
        return data

@dataclass(repr=False, frozen=True)
class _DictProxy(GenericProxy):
    args: Tuple[Type, Union[ModelSchema, Type]]
    _base_class = Dict
    
    @property
    def key(self):
        return self.args[0]
    @property
    def value(self):
        return self.args[1]
    
    def constructor(self, data: str) -> str:
        return f'{{ {data} }}'
    @classmethod
    def item_constructor(cls, data: Tuple[str, str]) -> str:
        return f'{data[0]}: {data[1]}'
    @classmethod
    def iterator(cls, data: str) -> str:
        return f'{data}.items()'

class _UnionProxyGen:
    def __getitem__(self, items: Tuple[Union[ModelSchema, Type, None], ...]) -> _UnionProxy:
        real_items = list()
        for it in items:
            is_generic, tp, args = extract_generic(it)
            if (tp == Union):
                it = UnionProxy[args]
            elif (tp == Optional):
                it = UnionProxy[args[0], None]
            else:
                list_append(real_items, it)
                continue
            
            if (isinstance(it, _UnionProxy)):
                list_extend(real_items, it.args)
        
        return _UnionProxy(tuple(real_items))

class _ListProxyGen:
    def __getitem__(self, tp: Union[ModelSchema, Type]):
        return _ListProxy((tp, ))

class _DictProxyGen:
    def __getitem__(self, tp: Tuple[Type, Union[ModelSchema, Type]]):
        return _DictProxy(tp)

UnionProxy = _UnionProxyGen()
ListProxy = _ListProxyGen()
DictProxy = _DictProxyGen()

T = TypeVar('T')
def list_append(lst: List[T], x: T):
    if (x not in lst):
        lst.append(x)

def list_extend(lst: List[T], it: Iterable[T]):
    for x in it:
        list_append(lst, x)

def extract_generic(tp: Type[T]) -> Tuple[bool, Type[T], Tuple[Type, ...]]:
    """
    Helper function that checks if the given type is generic,
    and if it is, expands it.
    
    Args:
        tp: `Type[T]` - potentially generic type.
    
    Returns:
        Returns a tuple of 3 values.
        
        - `bool`: **True** if the given type is `Generic`; **False** otherwise.
        - `Type[R]`: The class *T*, if *T* is not optional; and *R* if *T* is `Optional[R]`.
        - `Tuple[Type, ...]`: The tuple of class parameters used for *T*'s creation; empty tuple if it is not generic.
    
    Examples:
        ```python
        extract_generic(dict)                      # => (False, dict,    ())
        extract_generic(Dict[A, B])                # => (True,  Dict,    (A, B))
        extract_generic(Optional[int])             # => (True,  Union,   (int, None))
        extract_generic(MyClass[str])              # => (True,  MyClass, (str))
        extract_generic(Union[MyClass[str], None]) # => (True,  Union,   (MyClass[str], None))
        ```
    """
    
    if (isinstance(tp, GenericProxy)):
        # noinspection PyTypeChecker
        return True, tp.base, tp.args
    
    if (is_generic_type(tp)):
        base = get_origin(tp)
        return True, base, get_args(tp, evaluate=True)
    else:
        return False, tp, tuple()
del T

def generic_repr(cls: Union[_SpecialForm, GenericProxy], args: Tuple[Union[Type, GenericProxy, ModelClass, ModelSchema], ...], **kwargs) -> str:
    # noinspection PyProtectedMember,PyUnresolvedReferences
    return f"{cls._name}[{', '.join(class_name_pretty(t, **kwargs) for t in args)}]"

def class_name_pretty(cls: Union[Type, GenericProxy, ModelClass, ModelSchema], *, class_name_func: Converter = class_name) -> str:
    if (isinstance(cls, ModelSchema)):
        cls = cls.cls
    if (isinstance(cls, HavingPath)):
        return class_name_func(cls.pretty_path)
    else:
        is_generic, base, args = extract_generic(cls)
        if (is_generic):
            return generic_repr(base, args)
        else:
            return ref_name_pretty(base)

def ref_name_pretty(obj, full: bool=False) -> str:
    if (full):
        return f'{obj.__module__}.{ref_name_pretty(obj, full=False)}'
    else:
        try:
            return f'{obj.__qualname__}'
        except AttributeError:
            try:
                return f'{obj.__name__}'
            except AttributeError:
                return str(obj)

def ref_name_logger(cls: type) -> str:
    return '.'.join(map(package_name, ref_name_pretty(cls, full=True).split('.')))


__all__ = \
[
    'GenericProxy',
    'DictProxy',
    'ListProxy',
    'UnionProxy',
    
    'class_name_pretty',
    'extract_generic',
    'generic_repr',
    'ref_name_logger',
    'ref_name_pretty',
]
