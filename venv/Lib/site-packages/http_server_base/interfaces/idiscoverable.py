from abc import ABC
from typing import *

class IDiscoverable(ABC):
    @classmethod
    def get_public_ip(cls) -> str:
        pass

    @classmethod
    def self_discover(cls) -> Set[str]:
        """
        Server will try to do some self-discovery job.
        Not used in the distributed version.
        
        :return:
        The result is non-sorted set of unique items which could be associated with the local host.
        Usually it looks like:
        { '127.0.0.1', '127.0.1.1', 'localhost', 'MyComputer', '192.168.0.14' }
        """
        
        pass

__all__ = \
[
    'IDiscoverable',
]
