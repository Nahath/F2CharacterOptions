"""
Find the Kisbox (Container proto 63) in kladwtwn.map using the correct
88-byte object header (PID at +44, inv_count at +72).

Searches the objects section for the Container with proto 63 that is on
the same elevation as Sajag (elevation 0).
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\\Games\\Fallout 2")
MASTER = GAME / "master.dat"
RPU    = GAME / "mods" / "rpu.dat"

# Object section offsets
VANILLA_OBJ_START = 60324   # scripts_start=60312, 5 zero groups=12 bytes, OBJ_START=60324
PID_SAJAG  = 0x01000038     # critter proto 56
PID_KISBOX = 0x0000003F     # item proto 63 (Container)

# Item type → extra bytes in MAP record (from fallout2-ce source)
# These are the per-type extra fields in the MAP object record:
ITEM_EXTRA = {
    0: 0,   # Armor
    1: 0,   # Container
    2: 4,   # Drug  (3 fields × 4: effect1, effect2, effect3 or similar)
    3: 8,   # Weapon (ammo_quantity + ammo_type_pid)
    4: 4,   # Ammo  (magazine_quantity)
    5: 4,   # Misc  (charges)
    6: 4,   # Key   (key_code)
}
# Scenery subtype → extra bytes
SCENERY_EXTRA = {
    0: 0,   # Generic scenery
    1: 4,   # Door (walk_through)
    2: 8,   # Stairs (dest_tile + dest_map)
    3: 8,   # Elevator (type + level)
    4: 4,   # Ladder (dest_tile)  [LadderBottom]
    5: 4,   # Ladder (dest_tile)  [LadderTop]
}
EXIT_GRID_TYPE = 16  # Exit grid extra = 16 bytes


def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    try:
        with open(dat_path, "rb") as fh:
            fh.seek(-8, 2)
            tree_size, dat_size = struct.unpack("<II", fh.read(8))
            fh.seek(dat_size - tree_size - 8)
            tree = fh.read(tree_size)
        pos = 4
        while pos < len(tree):
            nl   = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
            comp = tree[pos]; pos += 1
            unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
            if name.replace("/", "\\") == target:
                with open(dat_path, "rb") as fh:
                    fh.seek(offset); raw = fh.read(packed)
                return zlib.decompress(raw) if comp else raw
    except OSError:
        pass
    return None


_proto_cache: dict[int, dict] = {}

def get_proto(proto_id: int) -> dict:
    if proto_id in _proto_cache:
        return _proto_cache[proto_id]
    for subdir in ("items", "critters", "scenery", "walls", "tiles"):
        filename = f"{proto_id:08d}.pro"
        data = read_dat(MASTER, f"proto\\{subdir}\\{filename}")
        if data is not None and len(data) >= 36:
            pid    = struct.unpack_from(">I", data, 0)[0]
            type_b = (pid >> 24) & 0xFF
            if len(data) >= 36:
                subtype = struct.unpack_from(">I", data, 32)[0]
            else:
                subtype = 0
            info = {"type": type_b, "subtype": subtype, "raw_pid": pid}
            _proto_cache[proto_id] = info
            return info
    _proto_cache[proto_id] = {}
    return {}


def extra_for_pid(pid: int) -> int:
    """Return the number of extra bytes for an object with this PID."""
    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF
    if type_byte == 0x01:  # critter
        return 40
    if type_byte == 0x00:  # item
        info = get_proto(proto_id)
        if not info:
            return 4   # conservative default
        return ITEM_EXTRA.get(info.get("subtype", 0), 4)
    if type_byte == 0x02:  # scenery
        info = get_proto(proto_id)
        subtype = info.get("subtype", 0)
        if subtype == 6:  # Exit grid
            return EXIT_GRID_TYPE
        return SCENERY_EXTRA.get(subtype, 0)
    # walls (0x03), tiles (0x04), misc (0x05)
    return 0


def parse_object(data: bytes, abs_pos: int) -> tuple[int, dict]:
    """Parse one 88-byte object record at abs_pos.
    Returns (total_bytes_consumed, info_dict)."""
    if abs_pos + 88 > len(data):
        raise ValueError(f"truncated at {abs_pos}")

    pid       = struct.unpack_from(">I", data, abs_pos + 44)[0]
    elev      = struct.unpack_from(">I", data, abs_pos + 40)[0]
    tile      = struct.unpack_from(">I", data, abs_pos +  4)[0]
    inv_count = struct.unpack_from(">I", data, abs_pos + 72)[0]

    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF
    extra     = extra_for_pid(pid)

    if inv_count > 1000:
        inv_count = 0   # safety clamp (shouldn't happen)

    consumed = 88 + extra

    children = []
    for _ in range(inv_count):
        if abs_pos + consumed + 4 > len(data):
            raise ValueError(f"qty truncated at {abs_pos+consumed}")
        qty = struct.unpack_from(">I", data, abs_pos + consumed)[0]
        consumed += 4
        child_bytes, child_info = parse_object(data, abs_pos + consumed)
        child_info["qty"] = qty
        children.append(child_info)
        consumed += child_bytes

    return consumed, {
        "abs":       abs_pos,
        "pid":       pid,
        "type_byte": type_byte,
        "proto_id":  proto_id,
        "elev":      elev,
        "tile":      tile,
        "inv_count": inv_count,
        "extra":     extra,
        "children":  children,
        "total":     consumed,
    }


def parse_objects_section(data: bytes, obj_start: int):
    pos    = obj_start
    total  = struct.unpack_from(">I", data, pos)[0]
    if total < 50000:
        pos += 4
    objects = []
    for elev in range(3):
        count = struct.unpack_from(">I", data, pos)[0]; pos += 4
        for _ in range(count):
            sz, info = parse_object(data, pos)
            objects.append(info)
            pos += sz
    return objects


# ── Load vanilla map ───────────────────────────────────────────────────────────
map_data = read_dat(MASTER, r"maps\kladwtwn.map")
if map_data is None:
    raise SystemExit("kladwtwn.map not found in master.dat")
print(f"Map: {len(map_data):,} bytes")

print("Parsing objects section (this may take a moment)...")
try:
    objects = parse_objects_section(map_data, VANILLA_OBJ_START)
    print(f"Parsed {len(objects)} top-level objects")
except Exception as e:
    print(f"Parse failed: {e}")
    raise SystemExit(1)

# ── Find Sajag ─────────────────────────────────────────────────────────────────
sajag = next((o for o in objects if o["pid"] == PID_SAJAG), None)
if sajag:
    print(f"\nSajag: abs={sajag['abs']}  elev={sajag['elev']}  tile={sajag['tile']}")
    print(f"  inv_count={sajag['inv_count']}  total_size={sajag['total']}")
    for i, item in enumerate(sajag["children"]):
        print(f"  item[{i}]: proto={item['proto_id']}  qty={item['qty']}  extra={item['extra']}")
else:
    print("\nSajag not found!")

# ── Find Kisbox ────────────────────────────────────────────────────────────────
kisboxes = [o for o in objects if o["pid"] == PID_KISBOX]
print(f"\nKisbox occurrences (proto 63, Container): {len(kisboxes)}")
for kb in kisboxes:
    print(f"  abs={kb['abs']}  elev={kb['elev']}  tile={kb['tile']}  "
          f"inv_count={kb['inv_count']}  total={kb['total']}")

# ── Find Kisbox near Sajag's elevation ─────────────────────────────────────────
if sajag and kisboxes:
    sajag_elev = sajag["elev"]
    near = [kb for kb in kisboxes if kb["elev"] == sajag_elev]
    print(f"\nKisbox objects on same elevation as Sajag ({sajag_elev}):")
    for kb in near:
        print(f"  abs={kb['abs']}  tile={kb['tile']}  inv_count={kb['inv_count']}")
        if kb["inv_count"] > 0:
            print(f"  First few items:")
            for i, c in enumerate(kb["children"][:5]):
                print(f"    [{i}] proto={c['proto_id']}  qty={c['qty']}  extra={c['extra']}")
            if kb["inv_count"] > 5:
                print(f"    ... ({kb['inv_count']} total)")

# ── Show Kisbox inv_count field offset and items section ───────────────────────
for kb in kisboxes[:1]:
    inv_count_abs = kb["abs"] + 72   # inv_count at base+72
    items_start   = kb["abs"] + 88 + kb["extra"]  # items start after base+extra
    print(f"\nKisbox patch info:")
    print(f"  abs_start        = {kb['abs']}")
    print(f"  inv_count field  = {inv_count_abs}  (value={kb['inv_count']})")
    print(f"  items_start      = {items_start}")
    print(f"  total_size       = {kb['total']}")
    print(f"  items_end (=abs_start+total) = {kb['abs']+kb['total']}")
