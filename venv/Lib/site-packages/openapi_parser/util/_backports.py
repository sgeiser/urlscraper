try:
    from functools import cached_property
except ImportError:
    from lazy_object_proxy.utils import cached_property

try:
    from functools import singledispatchmethod
except ImportError:
    from functools import singledispatch, update_wrapper
    class singledispatchmethod:
        """
        Single-dispatch generic method descriptor.
        Supports wrapping existing descriptors and handles non-descriptor
        callables as instance methods.
        """
        
        def __init__(self, func):
            if not callable(func) and not hasattr(func, "__get__"):
                raise TypeError(f"{func!r} is not callable or a descriptor")
            
            self.dispatcher = singledispatch(func)
            self.func = func
        
        def register(self, cls, method=None):
            """
            generic_method.register(cls, func) -> func
            Registers a new implementation for the given *cls* on a *generic_method*.
            """
            return self.dispatcher.register(cls, func=method)
        
        def __get__(self, obj, cls=None):
            def _method(*args, **kwargs):
                method = self.dispatcher.dispatch(args[0].__class__)
                # noinspection PyUnresolvedReferences
                return method.__get__(obj, cls)(*args, **kwargs)
            
            _method.__isabstractmethod__ = self.__isabstractmethod__
            _method.register = self.register
            update_wrapper(_method, self.func)
            return _method
        
        @property
        def __isabstractmethod__(self):
            return getattr(self.func, '__isabstractmethod__', False)


__all__ = \
[
    'cached_property',
    'singledispatchmethod',
]

__pdoc__ = \
{
    'cached_property': False,
    'singledispatchmethod': False,
}
