"""
Dump the raw bytes at the start of the objects section of kladwtwn.map
to determine the actual format at OBJ_START=283048.
"""
import struct, zlib
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
RPU  = GAME / "mods" / "rpu.dat"
OBJ_START = 283048

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl  = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        if name.replace("/", "\\") == target:
            with open(dat_path, "rb") as fh:
                fh.seek(offset); raw = fh.read(packed)
            return zlib.decompress(raw) if comp else raw
    return None

data = read_dat(RPU, r"maps\kladwtwn.map")
print(f"Map size: {len(data):,} bytes")

# Dump 256 bytes at OBJ_START as uint32 groups
print(f"\nBytes at OBJ_START={OBJ_START} (256 bytes, 4-byte groups):")
for i in range(0, 256, 4):
    pos = OBJ_START + i
    u = struct.unpack_from(">I", data, pos)[0]
    s = struct.unpack_from(">i", data, pos)[0]
    tb = (u >> 24) & 0xFF
    pid = u & 0xFFFFFF
    print(f"  +{i:4d} (abs={pos:7d}): {u:#010x}  ({s:12d})  type={tb} proto={pid}")

# Now try: skip the first int32 as total_count,
# then read elev counts directly
print(f"\n--- Trying: NO total_count header ---")
pos = OBJ_START
for elev in range(3):
    c = struct.unpack_from(">i", data, pos)[0]
    print(f"  Elevation {elev} count at +{pos-OBJ_START} (abs={pos}): {c}")
    if 0 <= c <= 10000:
        pos += 4
        for j in range(min(c, 3)):
            pid = struct.unpack_from(">i", data, pos+4)[0]
            tile = struct.unpack_from(">i", data, pos+12)[0]
            inv  = struct.unpack_from(">i", data, pos+64)[0]
            tb   = (pid >> 24) & 0xFF
            print(f"    obj[{j}]: pid={pid:#010x} type={tb} proto={pid&0xFFFFFF} tile={tile} inv={inv}")
        break
    else:
        print(f"  (invalid count, stopping)")
        break

# Search forward for valid elevation count (1..5000) followed by valid PID
print(f"\n--- Scanning for first plausible elevation count ---")
VALID_TYPES = {0,1,2,3,4,5}
for off in range(0, 512, 4):
    pos = OBJ_START + off
    count = struct.unpack_from(">i", data, pos)[0]
    if not (1 <= count <= 5000):
        continue
    # Check first object after this count
    obj_pos = pos + 4
    if obj_pos + 68 > len(data):
        continue
    pid = struct.unpack_from(">i", data, obj_pos + 4)[0]
    tile = struct.unpack_from(">i", data, obj_pos + 12)[0]
    tb = (pid >> 24) & 0xFF
    if tb not in VALID_TYPES:
        continue
    if not (0 <= tile <= 9999):
        continue
    print(f"  Candidate at +{off} (abs={pos}): count={count}, first obj pid={pid:#010x} type={tb} tile={tile}")
