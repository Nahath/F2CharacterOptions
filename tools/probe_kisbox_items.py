"""
Probe the Kisbox inventory in both vanilla and RPU maps using proper proto lookups.
Determines exact item sizes so we know where to append new items.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"
RPU    = GAME / "mods" / "rpu.dat"

ITEM_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}
SUBTYPE_NAMES = {0:"Armor",1:"Container",2:"Drug",3:"Weapon",4:"Ammo",5:"Misc",6:"Key"}


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
            nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
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


_proto_cache = {}

def get_item_subtype(proto_id):
    if proto_id in _proto_cache:
        return _proto_cache[proto_id]
    for src in [RPU, MASTER]:
        data = read_dat(src, f"proto\\items\\{proto_id:08d}.pro")
        if data and len(data) >= 36:
            subtype = struct.unpack_from(">I", data, 32)[0]
            _proto_cache[proto_id] = subtype
            return subtype
    _proto_cache[proto_id] = None
    return None


def extra_for_pid(pid):
    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF
    if type_byte == 0x01:
        return 40
    if type_byte == 0x00:
        st = get_item_subtype(proto_id)
        return ITEM_EXTRA.get(st, 4) if st is not None else 4
    return 0


def parse_items(data, pos, count, depth=0):
    """Parse `count` sequential item records starting at `pos`.
    Returns (end_pos, list_of_infos)."""
    indent = "  " * depth
    items = []
    for i in range(count):
        item_pos = pos
        if pos + 4 + 88 > len(data):
            print(f"{indent}  [TRUNCATED at {pos}]")
            break
        qty       = struct.unpack_from(">I", data, pos)[0]; pos += 4
        obj_start = pos
        pid       = struct.unpack_from(">I", data, obj_start + 44)[0]
        type_byte = (pid >> 24) & 0xFF
        proto_id  = pid & 0xFFFFFF
        inv_c     = struct.unpack_from(">I", data, obj_start + 72)[0]
        if inv_c > 500:
            inv_c = 0

        extra = extra_for_pid(pid)
        st = get_item_subtype(proto_id) if type_byte == 0 else None
        st_name = SUBTYPE_NAMES.get(st, "?") if st is not None else ("critter" if type_byte==1 else "?")

        print(f"{indent}  item[{i}]: abs={item_pos}  qty={qty}  pid={pid:#010x}  "
              f"proto={proto_id}  type={type_byte}  subtype={st}({st_name})  "
              f"extra={extra}  inv_c={inv_c}")

        pos += 88 + extra  # past header + extra

        if inv_c > 0:
            pos, sub = parse_items(data, pos, inv_c, depth+1)
        items.append({
            "abs": item_pos, "qty": qty, "pid": pid, "proto": proto_id,
            "type": type_byte, "subtype": st, "extra": extra, "inv_c": inv_c,
        })
    return pos, items


def probe(map_data, kisbox_abs, label):
    inv_count     = struct.unpack_from(">I", map_data, kisbox_abs + 72)[0]
    items_start   = kisbox_abs + 88
    inv_count_abs = kisbox_abs + 72

    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"  kisbox_abs={kisbox_abs}  inv_count={inv_count}  items_start={items_start}")
    print(f"  inv_count field at abs {inv_count_abs}")

    end_pos, items = parse_items(map_data, items_start, inv_count)
    print(f"  End of existing items: abs={end_pos}")
    print(f"  INSERT 3 new items at: abs={end_pos}")
    print(f"  Update inv_count at abs {inv_count_abs}: {inv_count} -> {inv_count+3}")
    return end_pos, inv_count


vanilla = read_dat(MASTER, r"maps\kladwtwn.map")
rpu_map = read_dat(RPU,    r"maps\kladwtwn.map")

# Vanilla Kisbox at tile=15121 (Sajag's barter box)
probe(vanilla, 113948, "VANILLA Kisbox tile=15121 (abs=113948)")

# RPU Kisbox at tile=15121
insert_pos, old_inv = probe(rpu_map, 158892, "RPU Kisbox tile=15121 (abs=158892)")

print(f"\n{'='*60}")
print(f"SUMMARY for RPU patch:")
print(f"  inv_count field:  abs {158892+72} = {158892+72:#x}  current={old_inv}  new={old_inv+3}")
print(f"  insert bytes at:  abs {insert_pos} = {insert_pos:#x}")
print(f"  Each new item:    4 (qty) + 88 (header) + 4 (Misc extra) = 96 bytes")
print(f"  Total insertion:  {3*96} bytes")
