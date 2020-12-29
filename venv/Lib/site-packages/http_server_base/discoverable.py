import socket
from typing import *

from .interfaces import IDiscoverable

class Discoverable(IDiscoverable):
    @classmethod
    def _self_discover_generator(cls):
        names = \
        [
            'localhost',
            socket.getfqdn(),
        ]
        for name in names:
            try:
                for _value in cls._self_discover_generator_per_interface(name=name):
                    yield _value
            except socket.herror:
                continue
        
        local_addr = cls.get_public_ip()
        try:
            for _value in cls._self_discover_generator_per_interface(addr=local_addr):
                yield _value
        except socket.herror:
            pass
    
    @classmethod
    def _self_discover_generator_per_interface(cls, name=None, addr=None):
        if (addr is None):
            assert not name is None, "Either name or addr is required"
            addr = socket.gethostbyname(name)
        yield addr
        _name, _alias_list, _address_list = socket.gethostbyaddr(addr)
        yield _name
        for _alias in _alias_list:
            yield _alias
        for addr in _address_list:
            yield addr
            yield socket.getfqdn(_name)
            yield socket.gethostbyname(_name)
    
    @classmethod
    def get_public_ip(cls) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_addr = s.getsockname()[0]
            s.close()
            return local_addr
        except OSError:
            return socket.gethostbyname(socket.gethostname())
    
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
        
        return set(cls._self_discover_generator())

__all__ = \
[
    'Discoverable',
]
