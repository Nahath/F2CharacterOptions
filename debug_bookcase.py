"""
Debug script: examine the Golden Gecko bookcase in the installed f2mod.dat.
Usage: python debug_bookcase.py <fallout2_dir>
"""
import struct
import sys
import zlib

BOOKCASE_TILE = 15069
BOOKCASE_PROTO = 70
KISBOX_TILE = 15121

_SUBTYPE_NAME = {0: "Armor", 1: "Container", 2: "Drug", 3: "Weapon",
                 4: "Ammo", 5: "Misc", 6: "Key"}
_ITEM_SUBTYPE_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}


def read_file_from_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
        pos = 4
        while pos < len(tree):
            name_len = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos + name_len].decode("latin-1").lower(); pos += name_len
            compression = tree[pos]; pos += 1
            uncompressed_size, packed_size, offset = struct.unpack_from("<III", tree, pos); pos += 12
            if name == target:
                fh.seek(offset)
                raw = fh.read(packed_size)
                return zlib.decompress(raw) if compression else raw
    return None


def proto_subtype_and_extra(dat_path, proto_id):
    """Read a proto from the given dat and return (subtype_int, extra_bytes)."""
    data = read_file_from_dat(dat_path, f"proto\\items\\{proto_id:08d}.pro")
    if data and len(data) >= 36:
        subtype = struct.unpack_from(">I", data, 32)[0]
        return subtype, _ITEM_SUBTYPE_EXTRA.get(subtype, 4)
    return None, 4


def parse_item(data, pos, dat_path, indent=0):
    """Parse one item slot; return (next_pos, info_dict)."""
    start = pos
    qty = struct.unpack_from(">I", data, pos)[0]
    pos += 4

    obj_id      = struct.unpack_from(">I", data, pos +  0)[0]
    tile        = struct.unpack_from(">I", data, pos +  4)[0]
    frm_pid     = struct.unpack_from(">I", data, pos + 32)[0]
    flags       = struct.unpack_from(">I", data, pos + 36)[0]
    elev        = struct.unpack_from(">I", data, pos + 40)[0]
    proto_pid   = struct.unpack_from(">I", data, pos + 44)[0]
    critter_idx = struct.unpack_from(">I", data, pos + 48)[0]
    script_pid  = struct.unpack_from(">I", data, pos + 64)[0]
    script_id   = struct.unpack_from(">I", data, pos + 68)[0]
    inv_count   = struct.unpack_from(">I", data, pos + 72)[0]
    max_slots   = struct.unpack_from(">I", data, pos + 76)[0]

    subtype, extra = proto_subtype_and_extra(dat_path, proto_pid)
    subtype_name = _SUBTYPE_NAME.get(subtype, f"?{subtype}")

    extra_bytes = data[pos + 88 : pos + 88 + extra]
    pos += 88 + extra

    info = {
        "abs_start":  start,
        "qty":        qty,
        "obj_id":     obj_id,
        "tile":       f"0x{tile:08X}" if tile == 0xFFFFFFFF else tile,
        "frm_pid":    frm_pid,
        "flags":      f"0x{flags:08X}",
        "elev":       elev,
        "proto_pid":  proto_pid,
        "critter_idx":f"0x{critter_idx:08X}",
        "script_pid": f"0x{script_pid:08X}",
        "script_id":  f"0x{script_id:08X}",
        "inv_count":  inv_count,
        "max_slots":  max_slots,
        "subtype":    subtype_name,
        "extra_bytes":extra_bytes.hex() if extra_bytes else "(none)",
        "total_bytes":pos - start,
    }

    pad = "  " * indent
    print(f"{pad}abs={start}  proto={proto_pid}  subtype={subtype_name}  qty={qty}")
    print(f"{pad}  obj_id={obj_id}  tile={'0x'+format(tile,'08X') if tile==0xFFFFFFFF else tile}")
    print(f"{pad}  flags={flags:#010x}  frm_pid={frm_pid}")
    print(f"{pad}  script_pid=0x{script_pid:08X}  script_id=0x{script_id:08X}")
    print(f"{pad}  inv_count={inv_count}  max_slots={max_slots}")
    print(f"{pad}  extra({extra}b): {extra_bytes.hex() if extra_bytes else '(none)'}")
    print(f"{pad}  total_bytes={pos - start}")

    # Parse nested items
    nested_start = pos
    for j in range(inv_count):
        print(f"{pad}  [nested item {j}]")
        pos, _ = parse_item(data, pos, dat_path, indent + 2)

    return pos, info


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_bookcase.py <fallout2_dir>")
        sys.exit(1)

    game_root = sys.argv[1]
    f2mod = game_root + "\\mods\\f2mod.dat"
    master = game_root + "\\master.dat"
    rpu = game_root + "\\mods\\rpu.dat"

    map_bytes = read_file_from_dat(f2mod, "maps\\kladwtwn.map")
    if map_bytes is None:
        print("kladwtwn.map not in f2mod.dat, trying rpu.dat...")
        map_bytes = read_file_from_dat(rpu, "maps\\kladwtwn.map")
    if map_bytes is None:
        print("Not found in rpu.dat either, trying master.dat...")
        map_bytes = read_file_from_dat(master, "maps\\kladwtwn.map")
    if map_bytes is None:
        print("ERROR: kladwtwn.map not found anywhere.")
        sys.exit(1)

    print(f"Map size: {len(map_bytes):,} bytes")
    data = map_bytes

    # --- Scan for bookcase candidates (same logic as install.py) ---
    print(f"\nScanning for bookcase (proto {BOOKCASE_PROTO}, tile {BOOKCASE_TILE})...")
    candidates = []
    seen = set()
    for proto_id in range(60, 71):
        needle = struct.pack(">I", proto_id)
        sp = 0
        while True:
            idx = data.find(needle, sp)
            if idx < 0:
                break
            obj = idx - 44
            if obj >= 0 and obj + 88 <= len(data) and obj not in seen:
                tile = struct.unpack_from(">I", data, obj + 4)[0]
                if 13000 <= tile <= 17000:
                    if not (proto_id == 63 and tile == KISBOX_TILE):
                        seen.add(obj)
                        candidates.append((obj, proto_id, tile))
                        print(f"  Candidate: abs={obj}  proto={proto_id}  tile={tile}")
            sp = idx + 1

    if not candidates:
        print("  No candidates found!")
        sys.exit(1)

    candidates.sort(key=lambda x: abs(x[2] - KISBOX_TILE))
    bookcase_abs, bookcase_proto, bookcase_tile = candidates[0]
    print(f"\nSelected bookcase: abs={bookcase_abs}  proto={bookcase_proto}  tile={bookcase_tile}")

    # --- Print bookcase object header ---
    print("\nBookcase header fields:")
    obj_id    = struct.unpack_from(">I", data, bookcase_abs +  0)[0]
    tile      = struct.unpack_from(">I", data, bookcase_abs +  4)[0]
    frm_pid   = struct.unpack_from(">I", data, bookcase_abs + 32)[0]
    flags     = struct.unpack_from(">I", data, bookcase_abs + 36)[0]
    elev      = struct.unpack_from(">I", data, bookcase_abs + 40)[0]
    proto_pid = struct.unpack_from(">I", data, bookcase_abs + 44)[0]
    inv_count = struct.unpack_from(">I", data, bookcase_abs + 72)[0]
    max_slots = struct.unpack_from(">I", data, bookcase_abs + 76)[0]
    print(f"  obj_id={obj_id}  tile={tile}  proto_pid={proto_pid}")
    print(f"  flags=0x{flags:08X}  elev={elev}  frm_pid={frm_pid}")
    print(f"  inv_count={inv_count}  max_slots={max_slots}")

    # --- Walk existing items ---
    print(f"\nBookcase items (inv_count={inv_count}):")
    pos = bookcase_abs + 88
    for i in range(inv_count):
        print(f"[item {i}]")
        pos, _ = parse_item(data, pos, master, indent=1)

    print(f"\nItems end at abs={pos}")

    # --- Look for Power Fist (proto 235) nearby ---
    pf_needle = struct.pack(">I", 235)
    print(f"\nSearching for Power Fist (proto 235) near abs={pos} (+/-500 bytes)...")
    search_from = max(0, pos - 200)
    search_to = min(len(data), pos + 200)
    chunk = data[search_from:search_to]
    pf_idx = chunk.find(pf_needle)
    if pf_idx >= 0:
        abs_pf = search_from + pf_idx
        print(f"  Found proto 235 at abs={abs_pf} (offset from items_end: {abs_pf - pos})")
        # The proto_pid is at +44 from obj start, so obj start = abs_pf - 44 + 4(qty) = abs_pf - 40
        pf_obj = abs_pf - 44  # without qty prefix
        pf_slot = pf_obj - 4   # with qty prefix
        print(f"\nPower Fist slot (assuming abs={pf_slot}):")
        if pf_slot >= search_from:
            parse_item(data, pf_slot, master, indent=1)
    else:
        print("  Power Fist NOT found near items_end!")
        # Search entire file
        idx2 = data.find(pf_needle, 60316)
        while idx2 >= 0:
            pf_slot2 = idx2 - 44 - 4
            if pf_slot2 >= 0:
                tile2 = struct.unpack_from(">I", data, pf_slot2 + 4 + 4)[0]
                print(f"  Proto 235 at abs={idx2} -> slot abs={pf_slot2}  tile={tile2:#010x}")
            idx2 = data.find(pf_needle, idx2 + 1)


if __name__ == "__main__":
    main()
