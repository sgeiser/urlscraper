from .date_formats import *
from .errors import *
from .filters import *
from .inheritance_support import *
from .loader import *
from .model_impl import *
from .path import *

__all__ = [ ]

_submodules = \
[
    date_formats,
    errors,
    filters,
    inheritance_support,
    loader,
    model_impl,
    path,
]

__pdoc__ = { }
for _submodule in _submodules:
    _submodule_name = _submodule.__name__.partition(f'{__name__}.')[-1]
    __all__.extend(_submodule.__all__)
    __pdoc__[_submodule_name] = True
    _submodule.__pdoc__ = getattr(_submodule, '__pdoc__', dict())
    _extras = getattr(_submodule, '__pdoc_extras__', list())
    for _element in _submodule.__all__:
        __pdoc__[_element] = _element in _extras
