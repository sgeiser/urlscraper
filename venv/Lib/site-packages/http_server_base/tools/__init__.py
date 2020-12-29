from .config_loader import *
from .dataclass_with_settings import *
from .defaults import *
from .errors import *
from .extensions import *
from .filters import *
from .inspect_tools import *
from .logging import *
from .path_tree_map import *
from .prefix_tree_map import *
from .re_dict import *
from .subrequest_classes import *
from .types import *

@property
def re_type():
    from warnings import warn
    from typing import Pattern
    warn("'re_type' is going to be deprecated. Use Pattern[str] instead", DeprecationWarning, 2)
    return Pattern[str]

__all__ = \
[
    're_type',
    'dataclass_with_settings',
    'with_settings',
]
__pdoc__ = { }
__pdoc_extras__ = [ ]

submodules = \
[
    config_loader,
    defaults,
    errors,
    extensions,
    filters,
    inspect_tools,
    logging,
    path_tree_map,
    prefix_tree_map,
    re_dict,
    subrequest_classes,
    types,
]

for _m in submodules: __all__.extend(_m.__all__)
from http_server_base.tools.docs import create_documentation_index
create_documentation_index(submodules, __name__, __pdoc__, __pdoc_extras__)
del create_documentation_index, submodules
