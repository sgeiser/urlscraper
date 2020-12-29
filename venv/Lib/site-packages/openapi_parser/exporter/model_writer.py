import dataclasses
import datetime
import enum
from typing import *

import dataclasses_json

from openapi_parser.model import ModelSchema, ModelClass, ModelEnumData
from openapi_parser.parser import OpenApiParser
from openapi_parser.util.utils import StrIO
from .abstract_writer import yielder, writer
from .class_writer import ClassWriter
from .footer_writer import FooterWriter
from .header_writer import HeaderWriter

class ModelWriter(ClassWriter, HeaderWriter, FooterWriter):
    
    @property
    def from_imports(self) -> Iterator[str]:
        imports = \
        [
            dataclasses.dataclass,
            dataclasses.field,
            dataclasses_json.config,
            dataclasses_json.dataclass_json,
            dataclasses_json.DataClassJsonMixin,
            dataclasses_json.LetterCase,
            datetime.date,
            datetime.datetime,
            datetime.time,
            enum.Enum,
        ]
        other_imports = \
        [
            'typing.*',
            '.utils.datetime_decoder',
            '.utils.discriminator_decoder',
        ]
        
        yield from self.objects_to_from_imports(imports)
        yield from other_imports
    
    def dump_model(self, parser: OpenApiParser) -> Iterator[str]:
        for path, mdl in parser.loaded_objects.items():
            if (isinstance(mdl, ModelSchema)):
                if (isinstance(mdl.cls, ModelEnumData)):
                    yield from self.dump_enum(mdl, mdl.cls)
                
                if (isinstance(mdl.cls, ModelClass) and not mdl.cls.merged):
                    yield from self.dump_class(mdl.cls)
    
    def dump_model_file(self, parser: OpenApiParser) -> Iterator[str]:
        yield from self.dump_headers()
        yield from self.dump_model(parser)
        yield from self.dump_footers()
    
    # region Writers
    @yielder
    def yield_model(self, parser: OpenApiParser) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_model(parser)
    
    @overload
    def write_model(self, parser: OpenApiParser) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_model(self, parser: OpenApiParser, *, file: StrIO) -> None:
        pass
    @writer
    def write_model(self, parser: OpenApiParser) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_model(parser)
    
    @yielder
    def yield_model_file(self, parser: OpenApiParser) -> Iterator[Tuple[int, str]]:
        # noinspection PyTypeChecker
        return self.dump_model_file(parser)
    
    @overload
    def write_model_file(self, parser: OpenApiParser) -> Iterator[str]:
        pass
    # noinspection PyOverloads
    @overload
    def write_model_file(self, parser: OpenApiParser, *, file: StrIO) -> None:
        pass
    @writer
    def write_model_file(self, parser: OpenApiParser) -> Optional[Iterator[str]]:
        # noinspection PyTypeChecker
        return self.yield_model_file(parser)
    # endregion


__all__ = \
[
    'ModelWriter',
]
