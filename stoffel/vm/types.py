"""
Type definitions for StoffelVM Python bindings
"""

from enum import IntEnum
from typing import Union, Any
from dataclasses import dataclass


class ValueType(IntEnum):
    """StoffelVM value types"""
    UNIT = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    STRING = 4
    OBJECT = 5
    ARRAY = 6
    FOREIGN = 7
    CLOSURE = 8
    SHARE = 9


class ShareType(IntEnum):
    """Types of secret shares supported by MPC operations"""
    INT = 0
    I32 = 1
    I16 = 2
    I8 = 3
    U8 = 4
    U16 = 5
    U32 = 6
    U64 = 7
    FLOAT = 8
    BOOL = 9


@dataclass
class StoffelValue:
    """
    Python representation of a StoffelVM value
    
    This class provides a convenient wrapper around StoffelVM values,
    handling the conversion between Python types and VM types.
    """
    value_type: ValueType
    data: Union[int, float, bool, str, bytes, tuple, None]
    
    @classmethod
    def unit(cls) -> "StoffelValue":
        """Create a unit value"""
        return cls(ValueType.UNIT, None)
    
    @classmethod
    def integer(cls, value: int) -> "StoffelValue":
        """Create an integer value"""
        return cls(ValueType.INT, value)
    
    @classmethod
    def float_value(cls, value: float) -> "StoffelValue":
        """Create a float value"""
        return cls(ValueType.FLOAT, value)
    
    @classmethod
    def boolean(cls, value: bool) -> "StoffelValue":
        """Create a boolean value"""
        return cls(ValueType.BOOL, value)
    
    @classmethod
    def string(cls, value: str) -> "StoffelValue":
        """Create a string value"""
        return cls(ValueType.STRING, value)
    
    @classmethod
    def object_ref(cls, object_id: int) -> "StoffelValue":
        """Create an object reference"""
        return cls(ValueType.OBJECT, object_id)
    
    @classmethod
    def array_ref(cls, array_id: int) -> "StoffelValue":
        """Create an array reference"""
        return cls(ValueType.ARRAY, array_id)
    
    @classmethod
    def foreign_ref(cls, foreign_id: int) -> "StoffelValue":
        """Create a foreign object reference"""
        return cls(ValueType.FOREIGN, foreign_id)
    
    @classmethod
    def share(cls, share_type: ShareType, share_bytes: bytes) -> "StoffelValue":
        """Create a secret share value"""
        return cls(ValueType.SHARE, (share_type, share_bytes))
    
    def to_python(self) -> Any:
        """Convert StoffelValue to native Python value"""
        if self.value_type == ValueType.UNIT:
            return None
        elif self.value_type in (ValueType.INT, ValueType.FLOAT, ValueType.BOOL, ValueType.STRING):
            return self.data
        elif self.value_type == ValueType.SHARE:
            # For shares, return a tuple of (ShareType, bytes)
            return self.data
        else:
            # For object/array/foreign references, return the ID
            return self.data
    
    def __repr__(self) -> str:
        return f"StoffelValue({self.value_type.name}, {self.data})"