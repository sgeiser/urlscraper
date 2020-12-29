from functools import wraps
from inspect import ismethod, signature, Parameter
from types import MethodType
from typing import *

from dataclasses import InitVar, field

from .inspect_tools import wrap_once, wrap_positional_args, filter_keyword_args, get_parameters

_SELF_NAME = 'self'
_INIT_NAME = '__init__'
_POST_INIT_NAME = '__post_init__'
_PREVENT_CONFIG_LOAD_FIELD_NAME = '_prevent_config_load'

def dataclass_with_settings(*x, settings_func: Union[str, Callable] = '_get_settings', settings_name: str = 'settings'):
    @wrap_once(name='dataclass_with_settings')
    def decorator(cls: type):
        cls.__annotations__[_PREVENT_CONFIG_LOAD_FIELD_NAME] = InitVar[bool]
        setattr(cls, _PREVENT_CONFIG_LOAD_FIELD_NAME, False)
        
        if (not hasattr(cls, settings_name)):
            cls.__annotations__[settings_name] = Dict[str, Any]
            setattr(cls, settings_name, field(init=True, repr=False, default=None))
        
        post_init: MethodType = getattr(cls, _POST_INIT_NAME, None)
        has_post_init = post_init is not None
        if (not has_post_init):
            def __post_init__(self, *args, **kwargs):
                pass
            # noinspection PyTypeChecker
            post_init = __post_init__
        
        post_init = with_settings(settings_func=settings_func, settings_name=settings_name)(post_init)
        post_init = wrap_positional_args(safe_wrap=False, cls=cls)(post_init)
        
        # if (has_post_init):
        #     sig = signature(post_init)
        #     params_list: List[Parameter] = list(sig.parameters.values())
        #     insert_before = [ *map(lambda p: p.kind in (Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD), params_list), True ].index(True)
        #     new_param = Parameter(_PREVENT_CONFIG_LOAD_FIELD_NAME, Parameter.KEYWORD_ONLY, default=False, annotation=bool)
        #     params_list.insert(insert_before, new_param)
        #     post_init.__signature__ = sig.replace(parameters=params_list)
        
        setattr(cls, _POST_INIT_NAME, post_init)
        
        return cls
    
    if (x):
        return decorator(*x)
    else:
        return decorator


def with_settings(*f, settings_func: str = '_get_settings', settings_name='settings'):
    @wrap_once(name='with_settings')
    def decorator(func):
        base_signature = get_parameters(func)
        
        @wraps(func)
        def wrapper(self, *args, _prevent_config_load: bool = False, **kwargs):
            if (not _prevent_config_load):
                _sfn = settings_func
                if (isinstance(_sfn, str)):
                    _sfn = getattr(self, _sfn)
                if (not ismethod(_sfn)):
                    args = self, *args
                _s = _sfn(*args, **kwargs)
                
                _s = filter_keyword_args(self.__init__, _s, denied_fields=[ _SELF_NAME ])
                _s[_PREVENT_CONFIG_LOAD_FIELD_NAME] = True
                self.__init__(**_s)
                getattr(self, settings_name).update(_s)
                return
            
            kwargs[_PREVENT_CONFIG_LOAD_FIELD_NAME] = True
            kwargs = filter_keyword_args(base_signature, kwargs, denied_fields=[ _SELF_NAME ])
            return func(self, *args, **kwargs)
        
        sig = signature(func)
        param = Parameter(_PREVENT_CONFIG_LOAD_FIELD_NAME, Parameter.KEYWORD_ONLY, default=False, annotation=bool)
        func.__signature__ = sig.replace(parameters=[ *sig.parameters.values(), param ])
        return wrapper
    
    if (f):
        return decorator(*f)
    else:
        return decorator

__all__ = \
[
    'dataclass_with_settings',
    'with_settings',
]
