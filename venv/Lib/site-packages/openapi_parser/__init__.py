"""
.. include:: ../../README.md
"""

from collections import namedtuple

__title__ = 'openapi-parser'
__author__ = 'Peter Zaitcev / USSX Hares'
__license__ = 'BSD 2-clause'
__copyright__ = 'Copyright 2020 Peter Zaitcev'
__version__ = '0.2.4'

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(*__version__.split('.'), releaselevel='alpha', serial=0)

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
