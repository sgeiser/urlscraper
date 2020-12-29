import os
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from typing import *

from openapi_parser.parser import OpenApiParser
from openapi_parser.util.utils import StrIO
from .abstract_writer import Writer
from .client_writer import ClientWriter
from .model_writer import ModelWriter
from .pacakge_init_writer import PackageInitWriter
from .utils_writer import UtilsWriter

class PackageWriter(Writer):
    parser: OpenApiParser
    destination_dir: str
    package_dir: str
    dry_run: bool
    
    def __init__(self, parser: OpenApiParser, destination_dir: AnyStr = '.code-gen/', package_name: Optional[AnyStr] = None, author: Optional[str] = None, *, dry_run: bool = False):
        if (isinstance(destination_dir, bytes)):
            destination_dir = destination_dir.decode()
        if (isinstance(package_name, bytes)):
            package_name = package_name.decode()
        
        if (package_name is None):
            package_name = self.package_name_pretty(parser.name or parser.metadata.name)
        
        if (destination_dir.endswith('/')):
            package_dir = self.field_name_pretty(package_name)
            destination_dir = os.path.join(destination_dir, package_dir)
        else:
            package_dir = os.path.basename(destination_dir)
        
        parser.name = package_name
        parser.author = author or parser.author or self.define_user()
        self.parser = parser
        self.package_dir = package_dir
        self.destination_dir = os.path.abspath(destination_dir)
        self.dry_run = dry_run
        super().__init__()
    
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def _subprocess(self, *args: str) -> Optional[str]:
        p = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if (out):
            return out.decode('utf-8').strip()
        else:
            return None
    
    def define_user(self) -> str:
        return self._subprocess('git', 'config', 'user.name') \
            or self._subprocess('git', 'config', 'user.email') \
            or os.environ.get('AUTHOR', None) \
            or os.environ.get('USERNAME', None) \
            or os.environ.get('USER', None) \
            or 'OpenAPI Parser'
    
    def filename(self, path: AnyStr) -> str:
        if (isinstance(path, bytes)):
            path = path.decode()
        
        if (not os.path.isabs(path)):
            path = os.path.join(self.destination_dir, path)
        
        return path
    
    def sub_package(self, name: AnyStr) -> 'PackageWriter':
        return PackageWriter(parser=self.parser, destination_dir=self.filename(name), package_name=self.parser.name)
    
    def open_file(self, path: AnyStr) -> StrIO:
        path = self.filename(path)
        dir = os.path.dirname(path)
        if (not os.path.isdir(dir) and not self.dry_run):
            os.makedirs(dir)
        
        self.logger.info("Writing file: '%s'...", path)
        if (self.dry_run): path = os.devnull
        return open(path, 'wt', encoding='utf8')
    
    def remove_package(self):
        if (self.dry_run): return
        shutil.rmtree(self.destination_dir, ignore_errors=True)
    
    def write_init(self):
        with self.open_file('__init__.py') as output:
            writer = PackageInitWriter()
            writer.write_package_init_file(self.parser, file=output)
    def write_utils(self):
        self.smart_writer(lambda: UtilsWriter(), lambda writer: writer.yield_utils_file(), 'utils')
    def write_model(self):
        self.smart_writer(lambda: ModelWriter(), lambda writer: writer.yield_model_file(self.parser), 'model')
    def write_client(self):
        with self.open_file('client.py') as output:
            writer = ClientWriter()
            writer.write_client_file(self.parser, file=output)
    
    def smart_writer(self, writer_gen: Callable[[], Writer], lines_gen: Callable[[Writer], Iterator[Tuple[int, str]]], module_name: str, *, max_lines: int = 5000):
        line_num = 0
        writer = writer_gen()
        with NamedTemporaryFile(mode='wt', newline=writer.NEWLINE, prefix=f'{module_name}-', suffix='.py', delete=False, encoding='utf8') as temp:
            for indent_level, line in lines_gen(writer):
                writer.write_line(temp, writer.join_line(indent_level, line))
                line_num += 1
        
        if (line_num < 2 * max_lines):
            with self.open_file(f'{module_name}.py') as dest: pass
            shutil.move(temp.name, dest.name)
        else:
            os.remove(temp.name)
            writer = writer_gen()
            self.partial_writer(lines_gen(writer), module_name, max_lines=max_lines, writer=writer)
    
    def partial_writer(self, lines: Iterator[Tuple[int, str]], module_name: str, *, max_lines: int = 5000, writer: Optional[Writer] = None):
        if (writer is None):
            writer = self
        
        with self.sub_package(module_name) as sub_package:
            line_num = 0
            part_num = 0
            file: Optional[StrIO] = None
            for indent_level, line in lines:
                if (file is None or indent_level == 0 and line == '' and line_num > max_lines):
                    if (file is not None):
                        file.close()
                    
                    file = sub_package.open_file(f'_{part_num + 1}.py')
                    if (part_num > 0):
                        writer.write_line(file, f'from ._{part_num} import *')
                    
                    part_num += 1
                    line_num = 0
                
                if (line.startswith('from .')):
                    line = 'from ..' + line[len('from .'):]
                
                writer.write_line(file, writer.join_line(indent_level, line))
                line_num += 1
            
            if (file is not None):
                file.close()
            
            with sub_package.open_file('__init__.py') as file:
                writer.write_line(file, f'from ._{part_num} import *')
                writer.write_line(file, f'from ._{part_num} import __all__')
    
    def write_package(self, *, clean: bool = False):
        if (clean):
            self.remove_package()
        
        self.write_init()
        self.write_utils()
        self.write_model()
        self.write_client()


__all__ = \
[
    'PackageWriter',
]
