"""Find Sajag's critter proto ID by scanning for ScriptID=80 (KCSajag)."""
import struct, zlib
from pathlib import Path

def list_and_read_prefix(dat_path, prefix):
    results = {}
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        if name.startswith(prefix.lower()):
            with open(dat_path, "rb") as fh2:
                fh2.seek(offset)
                raw = fh2.read(packed)
            results[name] = zlib.decompress(raw) if comp else raw
    return results

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

SAJAG_SCRIPT_IDX = 80

protos = list_and_read_prefix(game / "critter.dat", "proto\\critters\\")
print(f"Critter protos in critter.dat: {len(protos)}")

# Critter proto layout (big-endian):
#   0  PID (uint32)
#   4  TextID (uint32)
#   8  FrmID (uint32)
#  12  LightDist (uint16)
#  14  LightIntensity (uint16)
#  16  Flags (uint32)
#  20  ExtFlags (uint32)
#  24  unknown (uint32)
#  28  ScriptID (int32)   <- try this first (same as items)
# Also try 36, 44 in case layout differs for critters

for name, data in sorted(protos.items()):
    if len(data) < 52:
        continue
    pid = struct.unpack_from(">I", data, 0)[0]
    for offset in (28, 36, 44):
        if len(data) > offset + 4:
            sid = struct.unpack_from(">i", data, offset)[0]
            if sid == SAJAG_SCRIPT_IDX:
                print(f"  MATCH offset={offset}: {name}  PID={pid}  proto_id={pid & 0xFFFFFF}")
