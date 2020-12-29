from typing import *

from .path_tree_map import *

T = TypeVar('T')
class PrefixTreeMap(PathTreeMap[T]):
    
    def __init__(self, *args, **kwargs):
        if (args and isinstance(args[0], PathTreeMap)):
            parent, *args = args
            parent: PathTreeMap
            args = { k: v for k, v in parent.items() }, *args
        
        super().__init__(*args, **kwargs)
    
    def optimize(self) -> bool:
        optimized = False
        child_data = None
        for subtree in self.data.values():
            b = subtree.optimize()
            optimized = optimized or b
            child_data = subtree.value
        
        if (self.value is None or child_data == self.value):
            if (all(not subtree.has_child and subtree.value == child_data for subtree in self.data.values())):
                self.data.clear()
                self.value = child_data
                optimized = True
        
        return optimized
    
    def set(self, key: str, value: T, **kwargs):
        super().set(key, value, **kwargs, full_match=True)
    
    def _get_subtrees(self, *args, full_match: bool = False, **kwargs) -> Iterator['PrefixTreeMap']:
        if (not full_match and not self.has_child and self.value is not None):
            yield self
            return
        
        yield from super()._get_subtrees(*args, **kwargs)

__all__ = \
[
    'PrefixTreeMap',
]
