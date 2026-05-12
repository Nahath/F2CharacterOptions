"""
Dump the full byte content of both Kisbox objects in vanilla kladwtwn.map
to understand their structure and find which one is Sajag's barter box.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"
RPU    = GAME / "mods" / "rpu.dat"

# Item type → extra bytes in MAP format
ITEM_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}

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


def dump_object_header(data, obj_start, label=""):
    """Print all 88 header fields."""
    print(f"\n{'='*60}")
    print(f"Object at abs {obj_start}  [{label}]")
    fields = [
        (0, "field0/ObjID"), (4, "tile"), (8, "x"), (12, "y"),
        (16, "sx"), (20, "sy"), (24, "frame"), (28, "orientation"),
        (32, "frm_pid"), (36, "flags"), (40, "elevation"),
        (44, "proto_pid"), (48, "critter_idx"), (52, "light_rad"),
        (56, "light_int"), (60, "outline"), (64, "script_pid"),
        (68, "script_id"), (72, "inv_count"), (76, "max_slots"),
        (80, "unk10"), (84, "unk11"),
    ]
    for off, name in fields:
        v = struct.unpack_from(">I", data, obj_start + off)[0]
        s = struct.unpack_from(">i", data, obj_start + off)[0]
        print(f"  +{off:3d} ({name:12s}): {v:#010x} = {s:10d}")


def parse_item_properly(data, pos, depth=0):
    """Parse one inventory slot: qty(4) + object(88+extra+sub-items).
    Returns (total_bytes_consumed, info) or raises ValueError."""
    if pos + 4 + 88 > len(data):
        raise ValueError(f"truncated at {pos}")
    qty = struct.unpack_from(">I", data, pos)[0]
    pos += 4
    obj_start = pos

    pid       = struct.unpack_from(">I", data, obj_start + 44)[0]
    elev      = struct.unpack_from(">I", data, obj_start + 40)[0]
    inv_count = struct.unpack_from(">i", data, obj_start + 72)[0]
    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF

    if type_byte == 0x01:  # critter
        extra = 40
    elif type_byte == 0x00:  # item — look up subtype
        # We'll use a simple table: need proto to get subtype
        # For now use a rough default
        extra = 4   # most items are Misc/Ammo/Drug/Key = 4
    else:
        extra = 0

    if inv_count < 0 or inv_count > 500:
        inv_count = 0

    consumed = 88 + extra
    children = []
    for _ in range(inv_count):
        c_bytes, c_info = parse_item_properly(data, obj_start + consumed, depth+1)
        children.append(c_info)
        consumed += c_bytes

    total = 4 + consumed  # qty + object_record
    return total, {
        "qty":       qty,
        "abs":       obj_start,
        "pid":       pid,
        "type":      type_byte,
        "proto":     proto_id,
        "elev":      elev,
        "inv_count": inv_count,
        "extra":     extra,
        "consumed":  consumed,  # object record size
        "children":  children,
    }


# ── Load vanilla map ────────────────────────────────────────────────────────────
vanilla = read_dat(MASTER, r"maps\kladwtwn.map")
rpu_data = read_dat(RPU, r"maps\kladwtwn.map")

KISBOX_LOCS = [113948, 309716]  # vanilla
SAJAG_LOC   = 169348

print("=== VANILLA MAP KISBOX DUMP ===")
for loc in KISBOX_LOCS:
    dump_object_header(vanilla, loc, f"Kisbox at {loc}")
    inv_count = struct.unpack_from(">I", vanilla, loc + 72)[0]
    extra = 0  # Container has 0 extra bytes
    items_start = loc + 88 + extra
    print(f"\n  Items section starts at: {items_start}")
    print(f"  inv_count = {inv_count}")

    pos = items_start
    for i in range(min(inv_count, 100)):
        if pos + 4 + 88 > len(vanilla):
            print(f"  [item {i}]: truncated")
            break
        qty = struct.unpack_from(">I", vanilla, pos)[0]
        obj_pid = struct.unpack_from(">I", vanilla, pos + 4 + 44)[0]
        obj_inv = struct.unpack_from(">i", vanilla, pos + 4 + 72)[0]
        obj_tb  = (obj_pid >> 24) & 0xFF
        obj_pr  = obj_pid & 0xFFFFFF
        obj_ext = ITEM_EXTRA.get(obj_tb, 4) if obj_tb == 0 else (40 if obj_tb == 1 else 0)
        print(f"  item[{i}]: qty={qty}  pid={obj_pid:#010x}  type={obj_tb}  proto={obj_pr}"
              f"  inv={obj_inv}  extra={obj_ext}  abs={pos+4}")
        if obj_inv < 0 or obj_inv > 200:
            print(f"  [WARNING: suspicious inv_count={obj_inv} at item {i}, stopping]")
            break
        # Advance by qty(4) + header(88) + extra(obj_ext) + sub-items
        item_size = 4 + 88 + obj_ext  # ignoring sub-items for now
        pos += item_size

print(f"\n=== SAJAG DUMP (vanilla, abs={SAJAG_LOC}) ===")
dump_object_header(vanilla, SAJAG_LOC)

print(f"\n=== RPU KISBOX LOCS ===")
RPU_KISBOX_LOCS = [158892, 398892]
SAJAG_RPU = 220412
for loc in RPU_KISBOX_LOCS:
    inv_count = struct.unpack_from(">I", rpu_data, loc + 72)[0]
    tile      = struct.unpack_from(">I", rpu_data, loc + 4)[0]
    print(f"  Kisbox at {loc}: tile={tile}  inv_count={inv_count}")
