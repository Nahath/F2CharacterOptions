"""
Parse the Kisbox inventory in kladwtwn.map.
Uses proto files from master.dat to determine per-item EXTRA bytes.
Outputs exact byte offsets needed for patching.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"
RPU    = GAME / "mods" / "rpu.dat"

# Confirmed positions
SAJAG_PID     = 0x01000038  # critter proto 56
KISBOX_PID    = 0x0000003F  # item    proto 63 (Container)
SAJAG_VANILLA = 169388
SAJAG_RPU     = 220452
EXPECTED_SIZE = 488

# ItemType → extra bytes in MAP object record
ITEM_EXTRA = {
    0: 0,   # Armor
    1: 0,   # Container  (may be 4 — we validate below)
    2: 4,   # Drug
    3: 8,   # Weapon
    4: 4,   # Ammo
    5: 4,   # Misc
    6: 4,   # Key
}


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


_proto_cache: dict[int, int] = {}  # proto_id → extra bytes

def get_item_extra(proto_id: int) -> int:
    if proto_id in _proto_cache:
        return _proto_cache[proto_id]
    filename = f"{proto_id:08d}.pro"
    data = read_dat(MASTER, f"proto\\items\\{filename}")
    if data is not None and len(data) >= 36:
        item_type = struct.unpack_from(">I", data, 32)[0]
        extra = ITEM_EXTRA.get(item_type, 4)
    else:
        extra = 4  # conservative default
        print(f"  [warn] proto {proto_id} not found, defaulting extra=4")
    _proto_cache[proto_id] = extra
    return extra


def parse_object(data: bytes, abs_pos: int, sajag_base: int):
    """
    Parse one object record starting at abs_pos.
    Returns (bytes_consumed, info_dict).
    sajag_base used only for relative-offset display.
    """
    if abs_pos + 68 > len(data):
        raise ValueError(f"truncated at {abs_pos}")

    flags    = struct.unpack_from(">I", data, abs_pos +  0)[0]
    pid      = struct.unpack_from(">I", data, abs_pos +  4)[0]
    tile     = struct.unpack_from(">i", data, abs_pos + 12)[0]
    script   = struct.unpack_from(">i", data, abs_pos + 44)[0]
    inv_size = struct.unpack_from(">i", data, abs_pos + 64)[0]

    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF

    if type_byte == 0x01:       # critter
        extra = 0
    elif type_byte == 0x00:     # item
        extra = get_item_extra(proto_id)
    else:
        extra = 4

    if inv_size < 0:
        inv_size = 0

    consumed = 68 + extra

    children = []
    for _ in range(inv_size):
        if abs_pos + consumed + 4 > len(data):
            raise ValueError(f"qty truncated at {abs_pos+consumed}")
        qty = struct.unpack_from(">I", data, abs_pos + consumed)[0]
        consumed += 4
        child_bytes, child_info = parse_object(data, abs_pos + consumed, sajag_base)
        child_info["qty"] = qty
        children.append(child_info)
        consumed += child_bytes

    return consumed, {
        "abs":       abs_pos,
        "rel":       abs_pos - sajag_base,
        "pid":       pid,
        "type_byte": type_byte,
        "proto_id":  proto_id,
        "extra":     extra,
        "inv_size":  inv_size,
        "total":     consumed,
        "children":  children,
    }


# ── Load map ──────────────────────────────────────────────────────────────────

map_data = read_dat(MASTER, r"maps\kladwtwn.map")
if map_data:
    sajag_base = SAJAG_VANILLA
    src = "master.dat (vanilla)"
else:
    map_data = read_dat(RPU, r"maps\kladwtwn.map")
    sajag_base = SAJAG_RPU
    src = "rpu.dat"

if map_data is None:
    raise SystemExit("Could not read kladwtwn.map from master.dat or rpu.dat")

print(f"Map source : {src}  ({len(map_data):,} bytes)")
print(f"Sajag base : {sajag_base}")

# ── Parse Sajag ───────────────────────────────────────────────────────────────

sajag_bytes, sajag = parse_object(map_data, sajag_base, sajag_base)

print(f"\nSajag  pid=0x{sajag['pid']:08X}  inv_size={sajag['inv_size']}")
print(f"  computed size = {sajag_bytes}  (expected {EXPECTED_SIZE})")
if sajag_bytes != EXPECTED_SIZE:
    print("  *** SIZE MISMATCH — check EXTRA values ***")

# ── Find Kisbox ───────────────────────────────────────────────────────────────

kisbox = None
for i, item in enumerate(sajag["children"]):
    print(f"  Sajag inv[{i}]: qty={item['qty']}  proto={item['proto_id']}  "
          f"abs={item['abs']}  rel={item['rel']}  extra={item['extra']}")
    if item["pid"] == KISBOX_PID:
        kisbox = item

if kisbox is None:
    raise SystemExit("Kisbox (proto 63) not found in Sajag's inventory!")

print(f"\nKisbox abs={kisbox['abs']}  rel={kisbox['rel']}  "
      f"inv_size={kisbox['inv_size']}  extra={kisbox['extra']}")

# ── Kisbox sub-items ──────────────────────────────────────────────────────────

print(f"\nKisbox sub-items ({kisbox['inv_size']}):")
for i, child in enumerate(kisbox["children"]):
    print(f"  [{i:2d}] proto={child['proto_id']:4d}  qty={child['qty']:3d}  "
          f"extra={child['extra']}  size={child['total']:3d}  "
          f"abs={child['abs']}  rel={child['rel']}")

# ── Patch insertion point ─────────────────────────────────────────────────────

kisbox_hdr_end = kisbox["abs"] + 68 + kisbox["extra"]
if kisbox["children"]:
    last = kisbox["children"][-1]
    insert_abs = last["abs"] + last["total"]
else:
    insert_abs = kisbox_hdr_end

insert_rel = insert_abs - sajag_base

print(f"\nInsert new items at:")
print(f"  abs = {insert_abs}")
print(f"  rel = {insert_rel}  (offset from Sajag start)")
print(f"  Sajag record ends at abs={sajag_base+EXPECTED_SIZE}  rel={EXPECTED_SIZE}")

# ── Verify bytes at insertion point ──────────────────────────────────────────

print(f"\nBytes at/after insert point (4-byte words):")
for i in range(0, 32, 4):
    pos = insert_abs + i
    if pos + 4 <= len(map_data):
        v = struct.unpack_from(">I", map_data, pos)[0]
        print(f"  +{i:3d} (abs={pos}): {v:#010x}")
