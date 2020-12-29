from collections import namedtuple

__title__ = 'functional-python'
__author__ = 'Peter Zaitcev / USSX Hares'
__license__ = 'BSD 2-clause'
__copyright__ = 'Copyright 2019 Peter Zaitcev'
__version__ = '0.0.9'

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(*__version__.split('.'), releaselevel='alpha', serial=0)

from .predef import *
from .containers import *
from .monads import *

from .option import *

__all__ = \
[
    'version_info',
    '__title__',
    '__author__',
    '__license__',
    '__copyright__',
    '__version__',
    *predef.__all__,
    *containers.__all__,
    *monads.__all__,
    *option.__all__,
]
