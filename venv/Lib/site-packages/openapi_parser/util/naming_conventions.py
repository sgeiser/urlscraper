import re
from typing import Callable, List

import stringcase

Converter = Callable[[str], str]

def normalize(s: str) -> str:
    s = str(s)
    s = re.sub(r'\W', '_', s)
    s = re.sub(r'_{2,}', '_', s)
    return s.strip('_')

def smart_pascal_case(s: str) -> str:
    return stringcase.pascalcase(normalize(s))

def smart_snake_case(s: str) -> str:
    return normalize(re.sub(r'([A-Z](?=[^A-Z_]|$)|(?<=[a-z])[A-Z])', r'_\1', normalize(s)).lower())

def smart_kebab_case(s: str) -> str:
    return smart_snake_case(s).replace('_', '-')

def smart_const_case(s: str) -> str:
    return smart_snake_case(s).upper()

def name_parts(s: str) -> List[str]:
    return smart_snake_case(s).split('_')

class_name: Converter = smart_pascal_case
enum_entry_name: Converter = smart_pascal_case
field_name: Converter = smart_snake_case
const_name: Converter = smart_const_case
method_name: Converter = smart_snake_case
package_name: Converter = smart_kebab_case

def class_name_from_path(cls_path: str) -> str:
    return class_name(cls_path)


__all__ = \
[
    'Converter',
    
    'class_name',
    'class_name_from_path',
    'const_name',
    'enum_entry_name',
    'field_name',
    'method_name',
    'name_parts',
    'normalize',
    'package_name',
    'smart_const_case',
    'smart_kebab_case',
    'smart_pascal_case',
    'smart_snake_case',
]
