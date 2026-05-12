"""Check which mods contain kladwtwn.map."""
import struct
from pathlib import Path

MODS = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2\mods")
TARGET = r"maps\kladwtwn.map"

for dat in sorted(MODS.glob("*.dat")):
    try:
        with open(dat, "rb") as fh:
            fh.seek(-8, 2)
            ts, ds = struct.unpack("<II", fh.read(8))
            fh.seek(ds - ts - 8)
            tree = fh.read(ts)
        pos = 4
        while pos < len(tree):
            nl   = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
            comp = tree[pos]; pos += 1
            unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
            if name.replace("/", "\\") == TARGET:
                print(f"{dat.name}: HAS kladwtwn.map ({unc:,} bytes uncompressed)")
                break
    except Exception as e:
        print(f"{dat.name}: error - {e}")
