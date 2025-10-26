import io
import struct

def read_u32_le(f: io.BufferedReader) -> int:
    return struct.unpack("<I", f.read(4))[0]

def read_u64_le(f: io.BufferedReader) -> int:
    return struct.unpack("<Q", f.read(8))[0]

def _pack_u32(v: int) -> bytes:
    return struct.pack("<I", v)

def _pack_u64(v: int) -> bytes:
    return struct.pack("<Q", v)

def read_fixed_string(f: io.BufferedReader, size: int) -> str:
    raw = f.read(size)
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
