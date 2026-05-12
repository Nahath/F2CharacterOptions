"""
Locate the Kisbox container in kladwtwn.map and show its inventory.
Searches all map objects for containers near Sajag (proto 56).
Outputs the binary offset of the Kisbox's inv_size field and its contents.
"""
import struct, zlib, sys
from pathlib import Path
sys.setrecursionlimit(10000)

GAME = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
RPU  = GAME / "mods" / "rpu.dat"

# Confirmed objects-section start for kladwtwn.map (from find_obj_start.py)
OBJ_START = 283048

# PID high bytes
TYPE_ITEM    = 0x00
TYPE_CRITTER = 0x01

# Item extra bytes by PID type byte; critter = 40 extra bytes
EXTRA = {0x00: 4, 0x01: 40, 0x02: 4, 0x03: 4, 0x04: 0, 0x05: 4}


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


def parse_object(data, pos, depth=0):
    """
    Parse one object record starting at pos.
    Returns (size_in_bytes, info_dict).
    """
    if pos + 68 > len(data):
        raise ValueError(f"truncated at {pos}")
    pid       = struct.unpack_from(">i", data, pos +  4)[0]
    tile      = struct.unpack_from(">i", data, pos + 12)[0]
    script_id = struct.unpack_from(">i", data, pos + 44)[0]
    inv_size  = struct.unpack_from(">i", data, pos + 64)[0]   # signed; -1 = no inventory
    if inv_size < 0:
        inv_size = 0
    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF
    extra     = EXTRA.get(type_byte, 4)
    size      = 68 + extra

    # Guard: sane upper bound on inventory items
    if inv_size > 500:
        raise ValueError(f"Suspect inv_size={inv_size} at offset {pos} "
                         f"(pid=0x{pid&0xFFFFFFFF:08X} type={type_byte})")

    children  = []
    for _ in range(inv_size):
        if pos + size + 4 > len(data):
            raise ValueError(f"inventory qty truncated at {pos+size}")
        qty = struct.unpack_from(">I", data, pos + size)[0]
        size += 4
        child_size, child_info = parse_object(data, pos + size, depth + 1)
        child_info["qty"] = qty
        children.append(child_info)
        size += child_size
    return size, {
        "offset":     pos,
        "pid":        pid,
        "type_byte":  type_byte,
        "proto_id":   proto_id,
        "tile":       tile,
        "script_id":  script_id,
        "inv_size":   inv_size,
        "inv_offset": pos + 64,        # offset of the inv_size uint32 field
        "items_start": pos + 68 + extra, # byte where inventory data begins
        "payload_end": pos + size,     # byte after last inventory item
        "children":   children,
    }


def parse_all_objects(data, start):
    pos = start
    total = struct.unpack_from(">I", data, pos)[0]
    if total < 10000:
        pos += 4
    objects = []
    for elev in range(3):
        count = struct.unpack_from(">i", data, pos)[0]; pos += 4
        for _ in range(count):
            sz, info = parse_object(data, pos)
            info["elev"] = elev
            objects.append(info)
            pos += sz
    return objects


data = read_dat(RPU, r"maps\kladwtwn.map")
print(f"Map size: {len(data):,} bytes")

objects = parse_all_objects(data, OBJ_START)
print(f"Total objects parsed: {len(objects)}\n")

# Find Sajag (critter proto 56)
sajag = next((o for o in objects if o["type_byte"] == TYPE_CRITTER and o["proto_id"] == 56), None)
if sajag:
    print(f"Sajag: tile={sajag['tile']}  elev={sajag['elev']}  offset={sajag['offset']}")
else:
    print("Sajag not found!")
    sys.exit(1)

# Show all containers (items with inv_size > 0) on the same elevation as Sajag
print(f"\nContainers on elevation {sajag['elev']}:")
for o in objects:
    if o["elev"] == sajag["elev"] and o["type_byte"] == TYPE_ITEM and o["inv_size"] > 0:
        print(f"  proto={o['proto_id']:4d}  tile={o['tile']:6d}  inv_size={o['inv_size']}"
              f"  script_id={o['script_id']:4d}  offset={o['offset']}")
        for c in o["children"]:
            print(f"    child: proto={c['proto_id']:4d}  qty={c['qty']}  tile={c['tile']}")

# Also show any items in Sajag's direct inventory (nested in his object)
print(f"\nSajag's direct inventory ({sajag['inv_size']} items):")
for c in sajag["children"]:
    print(f"  proto={c['proto_id']:4d}  qty={c['qty']}  inv_size={c['inv_size']}"
          f"  script_id={c['script_id']}  offset={c['offset']}")
    for cc in c.get("children", []):
        print(f"    subitem: proto={cc['proto_id']:4d}  qty={cc['qty']}")
