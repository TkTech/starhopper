"""
Primitive types for high-level ESM records.
"""


class BaseType:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.value!r})>"


class UInt8(BaseType):
    pass


class UInt16(BaseType):
    pass


class UInt32(BaseType):
    pass


class UInt64(BaseType):
    pass


class Int8(BaseType):
    pass


class Int16(BaseType):
    pass


class Int32(BaseType):
    pass


class Int64(BaseType):
    pass


class Float(BaseType):
    pass


class Bool(BaseType):
    pass


class String(BaseType):
    pass


class Bytes(BaseType):
    pass


class Unknown(BaseType):
    pass
