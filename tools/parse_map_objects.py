"""
Parse Fallout 2 map objects section to find all critters and their proto_ids.
Uses the confirmed objects-section start offset of 283048 for kladwtwn.map.

F2 Object format (all big-endian):
  Base header (68 bytes):
    +0:  uint32  flags
    +4:  int32   PID        (type<<24 | proto_id)
    +8:  int32   CID
    +12: int32   tile_num   (-1 = not placed)
    +16: int32   tile_y     (always -1)
    +20: int32   sx
    +24: int32   sy
    +28: uint32  frame_idx
    +32: uint32  direction
    +36: uint32  FrmID
    +40: uint32  anim_code
    +44: int32   script_id  (local script slot, -1 = no script)
    +48: int32   next_obj
    +52: uint32  light_dist
    +56: uint32  light_intens
    +60: uint32  outline
    +64: uint32  inv_size   (# items in inventory)
  Type-specific extra (after base):
    Critter: 40 bytes
    Item:     4 bytes
    Scenery:  4 bytes
    Wall:     4 bytes
    Misc:     4 bytes
  Inventory (inv_size items, each = 4-byte qty + recursive object record)
"""
import struct, zlib
from pathlib import Path
import sys
sys.setrecursionlimit(5000)

EXTRA = {0: 4, 1: 40, 2: 4, 3: 4, 4: 0, 5: 4}  # extra bytes by type

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
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
        if name.replace("/", "\\") == target:
            with open(dat_path, "rb") as fh:
                fh.seek(offset)
                raw = fh.read(packed)
            return zlib.decompress(raw) if comp else raw
    return None

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
data = read_dat(game / "mods" / "rpu.dat", "maps\\kladwtwn.map")

# Confirmed start of objects section
OBJ_START = 283048

# Show raw bytes at the start to understand the structure
print("Bytes at objects section start:")
for i in range(0, 24, 4):
    val = struct.unpack_from(">I", data, OBJ_START + i)[0]
    print(f"  +{i}: {val} ({val:#010x})")

# The objects section has:
# int32  total_objects (sum across all elevations) -- OPTIONAL, may not exist
# For each elevation (0,1,2):
#   int32 count
#   [objects...]
# Try with and without the leading total count

print("\nTrying WITH leading total count:")
total = struct.unpack_from(">I", data, OBJ_START)[0]
print(f"  total = {total}")
pos = OBJ_START + 4
for elev in range(3):
    if pos + 4 > len(data):
        break
    count = struct.unpack_from(">i", data, pos)[0]
    print(f"  elev {elev} count = {count} (at offset {pos})")
    pos += 4

print("\nTrying WITHOUT leading total count (counts at elevation boundaries):")
pos = OBJ_START
for elev in range(3):
    if pos + 4 > len(data):
        break
    count = struct.unpack_from(">i", data, pos)[0]
    print(f"  elev {elev} count = {count} (at offset {pos})")
    pos += 4

# The total at start might be the total object count
# Let's try parsing: first int32 = total, then for each of 3 elevations: int32 count + objects
def parse_obj_size(data, pos, depth=0):
    """Return the byte size of one object record (base + extra + inventory)."""
    if pos + 68 > len(data):
        raise ValueError(f"truncated at {pos}")
    pid      = struct.unpack_from(">i", data, pos + 4)[0]
    inv_size = struct.unpack_from(">I", data, pos + 64)[0]
    obj_type = (pid >> 24) & 0xFF
    size     = 68 + EXTRA.get(obj_type, 4)
    for _ in range(inv_size):
        if size + pos + 4 > len(data):
            raise ValueError(f"inventory truncated at {pos+size}")
        qty_pos = pos + size
        size += 4  # quantity word
        sub_size = parse_obj_size(data, pos + size, depth + 1)
        size += sub_size
    return size

def parse_all_objects(data, pos):
    """Parse objects section; return list of (elev, pid, tile, script_id)."""
    # Try leading total first
    total = struct.unpack_from(">I", data, pos)[0]
    if total < 10000:
        pos += 4
    else:
        total = None

    objects = []
    for elev in range(3):
        count = struct.unpack_from(">i", data, pos)[0]; pos += 4
        if count < 0 or count > 20000:
            print(f"  Elevation {elev}: suspect count={count}, stopping")
            break
        print(f"  Elevation {elev}: {count} objects at offset {pos}")
        for i in range(count):
            pid       = struct.unpack_from(">i", data, pos + 4)[0]
            tile      = struct.unpack_from(">i", data, pos + 12)[0]
            script_id = struct.unpack_from(">i", data, pos + 44)[0]
            obj_type  = (pid >> 24) & 0xFF
            proto_id  = pid & 0xFFFFFF
            if obj_type == 1:
                objects.append((elev, proto_id, tile, script_id))
            try:
                sz = parse_obj_size(data, pos)
            except ValueError as e:
                print(f"    ERROR at object {i}: {e}")
                return objects
            pos += sz
    return objects

print("\nParsing objects section:")
objects = parse_all_objects(data, OBJ_START)
print(f"\nAll critters (type=1):")
for elev, proto_id, tile, script_id in objects:
    print(f"  elev={elev} proto={proto_id:3d}  tile={tile:5d}  script_slot={script_id}")
