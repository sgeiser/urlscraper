import datetime

from typing.re import *

from openapi_parser.util.utils import SearchableEnum

class DateFormatName(SearchableEnum):
    # DateFullYear  = 'date-fullyear'
    # DateMonth     = 'date-month'
    # DateMDay      = 'date-mday'
    # TimeHour      = 'time-hour'
    # TimeMinute    = 'time-minute'
    # TimeSecond    = 'time-second'
    # TimeSecFrac   = 'time-secfrac'
    # TimeNumOffset = 'time-numoffset'
    # TimeOffset    = 'time-offset'
    # PartialTime   = 'partial-time'
    FullDate      = 'date'
    FullTime      = 'time'
    DateTime      = 'date-time'

class DateFormatType(SearchableEnum):
    # PartialTime   = datetime.time
    FullDate      = datetime.date
    FullTime      = datetime.time
    DateTime      = datetime.datetime

# class DateFormatRegexp(SearchableEnum):
#     DateFullYear  = r'(\d{4})'
#     DateMonth     = r'(\d{2})'
#     DateMDay      = r'(\d{2})'
#     TimeHour      = r'(\d{2})'
#     TimeMinute    = r'(\d{2})'
#     TimeSecond    = r'(\d{2})'
#     TimeSecFrac   = r'\.(\d+)'
#     TimeNumOffset = rf'(([+-]){TimeHour}:{TimeMinute})'
#     TimeOffset    = rf'(?P<TimeOffset>Z|{TimeNumOffset})'
#     PartialTime   = rf'(?P<PartialTime>{TimeHour}:{TimeMinute}:{TimeSecond}(?:{TimeSecFrac})?)'
#     FullDate      = rf'(?P<FullDate>{DateFullYear}-{DateMonth}-{DateMDay})'
#     FullTime      = rf'(?P<FullTime>{PartialTime}{TimeNumOffset})'
#     DateTime      = rf'(?P<DateTime>{FullDate}T{FullTime})'

# class DateFormatCodes(SearchableEnum):
#     DateFullYear  = '%Y'
#     DateMonth     = '%m'
#     DateMDay      = '%d'
#     TimeHour      = '%H'
#     TimeMinute    = '%M'
#     TimeSecond    = '%S'
#     TimeSecFrac   = '.%f'
#     TimeNumOffset = '%z'
#     TimeOffset    = f'{TimeNumOffset}'
#     PartialTime   = f'{TimeHour}:{TimeMinute}:{TimeSecond}{TimeSecFrac}'
#     FullDate      = f'{DateFullYear}-{DateMonth}-{DateMDay}'
#     FullTime      = f'{PartialTime}{TimeNumOffset}'
#     DateTime      = f'{FullDate}T{FullTime}'


__all__ = \
[
    # 'DateFormatCodes',
    'DateFormatName',
    # 'DateFormatRegexp',
    'DateFormatType',
]
