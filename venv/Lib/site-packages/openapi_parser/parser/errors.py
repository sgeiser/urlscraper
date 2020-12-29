from dataclasses import dataclass
from typing import *


class OpenApiLoaderError(Exception):
    pass

@dataclass(frozen=True)
class InvalidSchema(OpenApiLoaderError, ValueError):
    object_path: str
    
    @property
    def message(self) -> str:
        return f"Schema '{self.object_path}' is invalid."

@dataclass(frozen=True)
class InvalidSchemaFields(InvalidSchema, ValueError):
    object_path: str
    comment: Optional[str] = None
    
    @property
    def message(self) -> str:
        msg =  f"Schema '{self.object_path}' has invalid combination of fields"
        if (self.comment):
            msg += ': ' + self.comment
        else:
            msg += '.'
        
        return msg

@dataclass(frozen=True)
class InvalidPropertyType(InvalidSchema, ValueError):
    property_name: str
    property_type: str
    
    @property
    def message(self) -> str:
        return f"Property '{self.property_name}' of class '{self.object_path}' has invalid type of '{self.property_type}'"

@dataclass(frozen=True)
class InvalidReference(OpenApiLoaderError, ValueError):
    ref: str
    
    @property
    def message(self) -> str:
        return f"Invalid reference: '{self.ref}'"
    
    def __post_init__(self):
        super().__init__(self.message)

@dataclass(frozen=True)
class InvalidReferenceFormat(InvalidReference):
    ref: str
    
    @property
    def message(self) -> str:
        return f"Invalid reference format: '{self.ref}'"

@dataclass(frozen=True)
class UnresolvedReference(InvalidReference, KeyError):
    ref: str
    
    @property
    def message(self) -> str:
        return f"The reference was mentioned but unresolved: '{self.ref}'"


__all__ = \
[
    'InvalidPropertyType',
    'InvalidReference',
    'InvalidReferenceFormat',
    'InvalidSchema',
    'InvalidSchemaFields',
    'OpenApiLoaderError',
    'UnresolvedReference',
]
