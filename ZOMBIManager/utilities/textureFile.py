from PIL import Image
import numpy as np
import os
import traceback
import struct
from dataclasses import dataclass

from typing import Optional
from utilities import bfz
from PySide6.QtWidgets import QFileDialog, QMessageBox

# TDTs
# NOTE: This is currently bad, I am pretty sure different platforms use different textures, if you opened up the WiiU version you might be able to get textures
# But for right now, this is screwed.
@dataclass
class TDTHeader:
    width: int
    height: int
    format: int
    data_offset: int

def parse_tdt_header(data: bytes) -> TDTHeader:
    if data[0x10:0x14] != b"TDT_":
        raise ValueError("Not a TDT file (bad magic)")

    # crude parse based on your sample
    width = struct.unpack_from("<H", data, 0x20)[0]
    height = struct.unpack_from("<H", data, 0x22)[0]
    fmt = struct.unpack_from("<I", data, 0x18)[0]
    data_offset = 0x40  # guess, refine later
    return TDTHeader(width, height, fmt, data_offset)

def decode_tdt(data: bytes) -> Optional[Image.Image]:
    hdr = parse_tdt_header(data)
    pixels = data[hdr.data_offset:]

    # try RGBA8888
    try:
        img = Image.frombytes("RGBA", (hdr.width, hdr.height), pixels, "raw", "BGRA")
        return img
    except Exception:
        pass

    # try RGB565 fallback
    try:
        arr = np.frombuffer(pixels, dtype=np.uint16).reshape(hdr.height, hdr.width)
        r = ((arr >> 11) & 0x1F) * 255 // 31
        g = ((arr >> 5) & 0x3F) * 255 // 63
        b = (arr & 0x1F) * 255 // 31
        rgba = np.dstack((r, g, b, np.full_like(r, 255, dtype=np.uint8)))
        return Image.fromarray(rgba.astype(np.uint8), "RGBA")
    except Exception:
        return None

def export_tdt_as_png(self, entry: bfz.BFZFileEntry):
    if not self.archive:
        return
    path, _ = QFileDialog.getSaveFileName(
        self, "Export PNG", os.path.splitext(entry.name)[0] + ".png"
    )
    if not path:
        return
    try:
        data = self.archive.read_file_bytes(entry)
        img = decode_tdt(data)
        if not img:
            raise RuntimeError("Unsupported/unknown TDT format")
        img.save(path)
        QMessageBox.information(self, "Exported", f"Exported PNG:\n{path}")
    except Exception as e:
        QMessageBox.critical(
            self,
            "Export error",
            f"Failed to export PNG:\n{e}\n\n{traceback.format_exc()}",
        )
