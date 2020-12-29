import functools
from collections import OrderedDict
from functools import wraps, reduce
from inspect import Signature, Parameter, signature, getmro, getmodule, ismethod, isfunction
from types import FunctionType, MethodType
from typing import *

from dataclasses_json import DataClassJsonMixin
from typing_inspect import is_generic_type, get_args, get_origin

def is_list_type(tp) -> bool:
    """
    Test if the type is a generic list type, including subclasses excluding
    non-generic classes.
    Examples::
    
    is_list_type(int) == False
    is_list_type(list) == False
    is_list_type(List) == True
    is_list_type(List[str, int]) == True
    class MyClass(List[str]):
        ...
    is_list_type(MyClass) == True
    """
    
    return is_generic_type(tp) and issubclass(get_origin(tp) or tp, List)

T = TypeVar('T')
@overload
def unfold_list_type(tp: Type[List[T]]) -> Type[T]:
    pass
@overload
def unfold_list_type(tp: Type[T]) -> None:
    pass
@overload
def unfold_list_type(tp: Any) -> None:
    pass
def unfold_list_type(tp: Union[Type[List[T]], Any]) -> Optional[Type[T]]:
    """
    Checks argument is Type[List[T]], and returns Type[T]; None otherwise
    Examples::
    
    unfold_list_type(int) == None
    unfold_list_type(list) == None
    unfold_list_type(List) == None
    unfold_list_type(List[int]) == int
    class MyClass(List[str]):
        ...
    unfold_list_type(MyClass) == None
    unfold_list_type(List[MyClass]) == MyClass
    
    :param tp: Type[List[T]] or Any
    :return: Optional[Type[T]]
    """
    
    if (not is_list_type(tp)):
        return None
    x = get_args(tp)
    if (x and isinstance(x, tuple)):
        if (len(x) == 1):
            x = x[0]
        else:
            return None
    
    if (x and isinstance(x, type)):
        # noinspection PyTypeChecker
        return x
    else:
        return None

_MT = DataClassJsonMixin
ModelType = TypeVar('ModelType', bound=_MT)
def unfold_json_dataclass_list_type(model: Union[Type[ModelType], Type[List[ModelType]]], *, check_match: bool = True) -> Tuple[Type[ModelType], bool]:
    """
    Checks argument is either Type[List[T]] or Type[T] where T is a json dataclass,
    and returns Type[T] and (is argument a list-type)
    Raises TypeError exception if T is not a json dataclass 
    
    Examples::
    
    @dataclass
    class MyJsonDataclass(DataClassJsonMixin):
        ...
    unfold_json_dataclass_list_type(MyJsonDataclass) == (MyJsonDataclass, False)
    unfold_json_dataclass_list_type(List[MyJsonDataclass]) == (MyJsonDataclass, True)
    
    # But!
    
    unfold_json_dataclass_list_type(int) # raises TypeError
    unfold_json_dataclass_list_type(list) # raises TypeError
    unfold_json_dataclass_list_type(List) # raises TypeError
    unfold_json_dataclass_list_type(List[int]) # raises TypeError
    class MyClass(List[str]):
        ...
    unfold_list_type(MyClass) # raises TypeError
    unfold_list_type(List[MyClass]) # raises TypeError
    
    :param model: Type[T] or Type[List[T]]
    :param check_match: bool (optional, default: True)
    If True, checks T is a json dataclass, and raises a TypeError if it is not.
    :return Type[T], bool
     - first: expanded type T
     - second: True if argument was List[T], False otherwise
    :raises TypeError if T is not a json dataclass
    """
    
    tp = unfold_list_type(model)
    if (tp is None):
        multi = False
        tp = model
    else:
        multi = True
    
    if (check_match):
        if (not issubclass(tp, _MT)):
            raise TypeError(f"'{tp}' from '{model}' (type: '{type(model)}') is neither a json dataclass nor list of json dataclass")
    
    return tp, multi

_DEFAULT = object()
AUTO = object()

# Update functools.wraps to support wrap_once correctly working
_DECORATION_ATTRIBUTE = '__decorations__'
functools.WRAPPER_ASSIGNMENTS = *functools.WRAPPER_ASSIGNMENTS, _DECORATION_ATTRIBUTE

ParameterContainer = Union[FunctionType, MethodType, Signature, List[Parameter]]

def wrap_once(*f, name: str = None):
    def wrapper(decorator: FunctionType):
        decor_name = name
        if (decor_name is None):
            decor_name = decorator.__name__
        
        @wraps(decorator)
        def wrapped_decorator(func):
            if (not hasattr(func, _DECORATION_ATTRIBUTE)):
                setattr(func, _DECORATION_ATTRIBUTE, list())
            decorations: List[str] = getattr(func, _DECORATION_ATTRIBUTE)
            if (decor_name in decorations):
                return func
            else:
                decorations.append(decor_name)
                return decorator(func)
        return wrapped_decorator
    
    if (f):
        return wrapper(*f)
    else:
        return wrapper


def get_class_that_defined_method(meth: Union[FunctionType, MethodType]) -> Type:
    if ismethod(meth):
        for cls in getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__):
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if isfunction(meth):
        cls = getattr(getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def get_parameters(x: ParameterContainer) -> List[Parameter]:
    if (callable(x)):
        x = signature(x)
    if (isinstance(x, Signature)):
        x = x.parameters
    if (hasattr(x, 'values')):
        x = x.values()
    if (not isinstance(x, list)):
        x = list(x)
    
    return x

def has_var_keyword_args(x: ParameterContainer) -> bool:
    return any(p.kind == Parameter.VAR_KEYWORD for p in get_parameters(x))

def get_positional_or_keyword_arguments(x: ParameterContainer) -> List[Parameter]:
    return [ p for p in get_parameters(x) if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.KEYWORD_ONLY, Parameter.POSITIONAL_OR_KEYWORD) ]

def combine_signatures(child: Dict[str, Parameter], parent: Dict[str, Parameter]) -> Dict[str, Parameter]:
    result = OrderedDict()
    def insert(name, parameter):
        if (name not in result):
            result[name] = parameter
    
    for name, parameter in child.items():
        if (parameter.kind == Parameter.VAR_POSITIONAL):
            for p_name, p_parameter in parent.items():
                if (p_parameter.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.VAR_POSITIONAL)):
                    insert(p_name, p_parameter)
        elif (parameter.kind == Parameter.VAR_KEYWORD):
            for p_name, p_parameter in parent.items():
                if (p_parameter.kind in (Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD)):
                    insert(p_name, p_parameter)
        else:
            insert(name, parameter)
    
    return result

def get_combined_signature(cls: Type, method_name: str) -> Dict[str, Parameter]:
    classes = getmro(cls)
    methods = list()
    for c in classes:
        m = getattr(c, method_name, _DEFAULT)
        if (m is _DEFAULT):
            break
        elif (all(x is not m for x in methods)):
            methods.append(m)
    return reduce(combine_signatures, map(lambda m: signature(m).parameters, methods))

def get_positional_args_wrapper(function: FunctionType, parameters: Dict[str, Parameter], *, safe_wrap: bool, discard_extra_args: bool):
    params_list = list(parameters.values())
    positional_args = [ p for p in params_list if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD) ]
    keyword_only_args = [ p for p in params_list if p.kind in (Parameter.KEYWORD_ONLY, ) ]
    var_args = [ p for p in params_list if p.kind == Parameter.VAR_POSITIONAL ]
    has_var_args = any(var_args)
    
    def positional_parameters(args) -> Iterator[Parameter]:
        yielded = 0
        yield from positional_args
        yielded += len(positional_args)
        
        if (has_var_args):
            while (True):
                yield var_args[0]
        if (not safe_wrap):
            yield from keyword_only_args
            yielded += len(keyword_only_args)
        
        raise TypeError(f"{function} takes at most {yielded} positional parameters, but {len(args)} were given")
    
    @wraps(function)
    def wrapper(*args, **kwargs):
        gen = positional_parameters(args)
        
        new_args = list()
        shifted = False
        
        for arg in args:
            p = next(gen)
            if (p.kind in (Parameter.VAR_POSITIONAL, Parameter.POSITIONAL_ONLY)):
                if (shifted):
                    if (discard_extra_args):
                        raise TypeError(f"{function}: Cannot wrap positional arguments")
                    else:
                        break
                else:
                    new_args.append(arg)
            else:
                shifted = True
                kwargs[p.name] = arg
        
        return function(*new_args, **kwargs)
    return wrapper

def filter_keyword_args(f: ParameterContainer, kwargs: Dict[str, Any], *, allowed_fields: List[str] = None, denied_fields: List[str] = None, has_kwargs: bool = None):
    if (allowed_fields is None):
        has_kwargs = has_var_keyword_args(f)
        allowed_fields = list(map(lambda p: p.name, get_positional_or_keyword_arguments(f)))
    elif (has_kwargs is None):
        has_kwargs = False
    
    if (denied_fields is None):
        denied_fields = list()
    return { p: v for p, v in kwargs.items() if ((has_kwargs or p in allowed_fields) and p not in denied_fields) }


def wrap_positional_args(*f, safe_wrap: bool = True, discard_extra_args: bool = False, super: Union[Type, Tuple[Type], str, None] = None, cls: Type = _DEFAULT):
    _super = super
    @wrap_once(name='wrap_positional_args')
    def decorator(func: FunctionType):
        nonlocal _super
        _class = cls
        if (cls is not _DEFAULT):
            pass
        elif (isinstance(_super, tuple)):
            pass
        elif (_super is None):
            _class = None
        elif (isinstance(_super, type)):
            _super = _super, 
        elif (_super is 'auto'):
            try:
                _class = get_class_that_defined_method(func)
            except AttributeError:
                _class = _DEFAULT
        else:
            raise ValueError(f"Invalid type of argument 'super': expected tuple, type, or None, got {type(_super)}")
        
        if (_class is None):
            sig = signature(func).parameters
        else:
            _func_name = func.__name__
            if (_class is _DEFAULT):
                _class = type('_meta', _super, { _func_name: func })
            
            sig = get_combined_signature(_class, _func_name)
        
        return get_positional_args_wrapper(func, sig, safe_wrap=safe_wrap, discard_extra_args=discard_extra_args)
    
    if (f):
        return decorator(*f)
    else:
        return decorator

__all__ = \
[
    'combine_signatures',
    'filter_keyword_args',
    'get_class_that_defined_method',
    'get_combined_signature',
    'get_parameters',
    'get_positional_or_keyword_arguments',
    'has_var_keyword_args',
    'is_list_type',
    'unfold_json_dataclass_list_type',
    'unfold_list_type',
    'wrap_once',
    'wrap_positional_args',
]
