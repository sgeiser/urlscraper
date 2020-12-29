from typing import *

def create_documentation_index(submodules: list, __name__: str, __pdoc__: Dict[str, Union[str, bool]], __pdoc_extras__: List[str]):
    for submodule in submodules:
        submodule_name = submodule.__name__.partition(f'{__name__}.')[-1]
        __pdoc__[submodule_name] = True
        submodule_extras = getattr(submodule, '__pdoc_extras__', list())
        for _element in submodule.__all__:
            __pdoc__[_element] = _element in submodule_extras
        __pdoc_extras__.extend(submodule_extras)

__all__ = \
[
    'create_documentation_index',
]
__pdoc_extras__ = \
[
    'create_documentation_index',
]
