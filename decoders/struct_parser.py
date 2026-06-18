import struct

class StructParser:
    @staticmethod
    def read_uint8(data, offset):
        return struct.unpack_from('<B', data, offset)[0]

    @staticmethod
    def read_uint16(data, offset, big_endian=False):
        fmt = '>H' if big_endian else '<H'
        return struct.unpack_from(fmt, data, offset)[0]

    @staticmethod
    def read_uint32(data, offset, big_endian=False):
        fmt = '>I' if big_endian else '<I'
        return struct.unpack_from(fmt, data, offset)[0]

    @staticmethod
    def read_float(data, offset, big_endian=False):
        fmt = '>f' if big_endian else '<f'
        return struct.unpack_from(fmt, data, offset)[0]

    @staticmethod
    def read_string(data, offset, length):
        raw = data[offset:offset + length]
        return raw.split(b'\x00')[0].decode('utf-8', errors='replace')
