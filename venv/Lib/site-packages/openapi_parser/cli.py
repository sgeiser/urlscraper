import sys
from logging import getLogger, StreamHandler
from typing import *

from .exporter import PackageWriter
from .model import HavingId
from .parser.loader import *
from .util.utils import list_pop_any

JUSTIFICATION_SIZE = 140
def get_logger(verbose: bool = False):
    logger = getLogger('openapi-parser')
    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    if (verbose):
        handler.setLevel('DEBUG')
        logger.setLevel('DEBUG')
    else:
        handler.setLevel('INFO')
        logger.setLevel('INFO')
    
    return logger

def run(schema_file: str, *writer_args, verbose: bool = False, dry_run: bool = False) -> int:
    logger = get_logger(verbose=verbose)
    
    parser = OpenApiParser.open(schema_file)
    parser.load_all()
    
    for path, mdl in parser.loaded_objects.items():
        logger.debug(('# ' + type(mdl).__name__ + (f" '{mdl.id}'" if isinstance(mdl, HavingId) else '')).ljust(JUSTIFICATION_SIZE, ' ') + f" -- '{path}'")
    logger.debug('# ' + '=' * JUSTIFICATION_SIZE)
    logger.debug('')
    
    package_writer = PackageWriter(parser, *writer_args, dry_run=dry_run)
    package_writer.write_package(clean=True)
    return 0

def cli(args: Optional[List[str]] = None) -> int:
    if (args is None):
        args = sys.argv[1:]
    
    if (len(args) < 1):
        print(f"Not enough arguments, usage: python -m openapi_parser SCHEMA [DESTINATION] [PACKAGE_NAME]", file=sys.stderr)
        return 1
    
    verbose = bool(list_pop_any(args, '-v', '--verbose'))
    schema_file = args.pop(0)
    
    return run(schema_file, *args, verbose=verbose)


__all__ = \
[
    'cli',
    'run',
    'get_logger',
    'JUSTIFICATION_SIZE',
]
__pdoc_extras__ = \
[
    'JUSTIFICATION_SIZE',
]
