"""
.. include:: ../../README.md
"""

from collections import namedtuple

__title__ = 'http-server-base'
__author__ = 'Peter Zaitcev / USSX Hares'
__license__ = 'MIT Licence'
__copyright__ = 'Copyright 2018-2020 Peter Zaitcev'
__version__ = '2.0.5'

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(*__version__.split('.'), releaselevel='alpha', serial=0)

from .application_base import *
from .daemon import *
from .discoverable import *
from .empty_request_handler import *
from .error_matcher import *
from .handler_controller import *
from .health_check_request_handler import *
from .host import Host
from .interfaces import *
from .logged_request_handler import *
from .prefix_tree_router import *
from .request_logger_client import *
from .responders import *
from .strict_host_matches import *
from .subrequest_client import *

__all__ = \
[
    'version_info',
    '__title__',
    '__author__',
    '__license__',
    '__copyright__',
    '__version__',
]
__pdoc__ = { }
__pdoc_extras__ = [ ]

submodules = \
[
    application_base,
    daemon,
    discoverable,
    empty_request_handler,
    error_matcher,
    handler_controller,
    health_check_request_handler,
    host,
    interfaces,
    logged_request_handler,
    prefix_tree_router,
    request_logger_client,
    responders,
    strict_host_matches,
    subrequest_client,
]

for _m in submodules: __all__.extend(_m.__all__)
from http_server_base.tools.docs import create_documentation_index
create_documentation_index(submodules, __name__, __pdoc__, __pdoc_extras__)
del create_documentation_index, submodules
