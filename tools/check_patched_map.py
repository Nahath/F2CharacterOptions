"""
Verify the patched kladwtwn.map inside f2mod.dat:
- MAP header (version, player start tile/elevation/orientation, flags)
- Kisbox inv_count and item structure
- Object after Kisbox to confirm no corruption
"""
import struct, zlib
from pathlib import Path

GAME    = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
F2MOD   = GAME / "mods" / "f2mod.dat"
RPU     = GAME / "mods" / "rpu.dat"
MASTER  = GAME / "master.dat"

PID_KISBOX  = 0x0000003F
KISBOX_TILE = 15121

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


def dump_header(data):
    print("=== MAP HEADER ===")
    fields = [
        (0,   "version"),
        (4,   "map_name (16 chars)"),
        (20,  "player_start_tile"),
        (24,  "player_start_elev"),
        (28,  "player_start_orient"),
        (32,  "num_local_vars"),
        (36,  "script_id"),
        (40,  "flags"),
        (44,  "elevation_flags"),
        (48,  "darkness"),
        (52,  "num_global_vars"),
        (56,  "map_id"),
        (60,  "time"),
    ]
    for off, name in fields:
        if name == "map_name (16 chars)":
            val = data[off:off+16].split(b"\x00")[0].decode("latin-1")
            print(f"  +{off:3d} ({name}): {val!r}")
        else:
            v = struct.unpack_from(">I", data, off)[0]
            s = struct.unpack_from(">i", data, off)[0]
            print(f"  +{off:3d} ({name:25s}): {v:#010x} = {s}")


def find_kisbox(data):
    needle = struct.pack(">I", PID_KISBOX)
    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx < 0:
            return None
        obj = idx - 44
        if obj >= 0 and obj + 88 <= len(data):
            tile = struct.unpack_from(">I", data, obj + 4)[0]
            if tile == KISBOX_TILE:
                return obj
        pos = idx + 1
    return None


def dump_item(data, pos, label=""):
    if pos + 4 + 88 > len(data):
        print(f"  {label}: TRUNCATED at {pos}")
        return pos
    qty = struct.unpack_from(">I", data, pos)[0]
    obj = pos + 4
    oid   = struct.unpack_from(">I", data, obj +  0)[0]
    tile  = struct.unpack_from(">I", data, obj +  4)[0]
    frm   = struct.unpack_from(">I", data, obj + 32)[0]
    flags = struct.unpack_from(">I", data, obj + 36)[0]
    elev  = struct.unpack_from(">I", data, obj + 40)[0]
    pid   = struct.unpack_from(">I", data, obj + 44)[0]
    inv_c = struct.unpack_from(">I", data, obj + 72)[0]
    print(f"  {label}: abs={pos}  qty={qty}  ObjID={oid}  tile={tile:#010x}  "
          f"frm_pid={frm:#010x}  flags={flags:#010x}  elev={elev}  "
          f"pid={pid:#010x}  inv_c={inv_c}")
    return obj


map_data = read_dat(F2MOD, r"maps\kladwtwn.map")
if map_data is None:
    print("ERROR: kladwtwn.map not in f2mod.dat")
    exit(1)

print(f"kladwtwn.map from f2mod.dat: {len(map_data):,} bytes\n")
dump_header(map_data)

kisbox = find_kisbox(map_data)
if kisbox is None:
    print("\nERROR: Kisbox not found")
    exit(1)

inv_count = struct.unpack_from(">I", map_data, kisbox + 72)[0]
print(f"\n=== KISBOX at abs={kisbox}, inv_count={inv_count} ===")

# Also compare against RPU original
rpu_map = read_dat(RPU, r"maps\kladwtwn.map")
if rpu_map:
    rpu_kb = find_kisbox(rpu_map)
    rpu_inv = struct.unpack_from(">I", rpu_map, rpu_kb + 72)[0] if rpu_kb else "?"
    print(f"  (RPU original: kisbox at {rpu_kb}, inv_count={rpu_inv})")
    print(f"  Map size delta: {len(map_data) - len(rpu_map):+d} bytes (expected +288)")

ITEM_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}

def get_subtype(proto_id):
    for dat in [RPU, MASTER]:
        d = read_dat(dat, f"proto\\items\\{proto_id:08d}.pro")
        if d and len(d) >= 36:
            return struct.unpack_from(">I", d, 32)[0]
    return None

pos = kisbox + 88
for i in range(inv_count):
    qty = struct.unpack_from(">I", map_data, pos)[0]
    obj = pos + 4
    pid   = struct.unpack_from(">I", map_data, obj + 44)[0]
    proto = pid & 0xFFFFFF
    tb    = (pid >> 24) & 0xFF
    frm   = struct.unpack_from(">I", map_data, obj + 32)[0]
    flags = struct.unpack_from(">I", map_data, obj + 36)[0]
    oid   = struct.unpack_from(">I", map_data, obj +  0)[0]

    if tb == 0:
        st = get_subtype(proto)
        extra = ITEM_EXTRA.get(st, 4) if st is not None else 4
    elif tb == 1:
        extra = 40
    else:
        extra = 0

    print(f"  item[{i}]: abs={pos}  qty={qty}  pid={pid:#010x}  proto={proto}  "
          f"frm={frm:#010x}  flags={flags:#010x}  ObjID={oid}  extra={extra}")
    pos += 4 + 88 + extra

print(f"\n  End of Kisbox items: abs={pos}")

# Show the next object after the Kisbox items
print(f"\n=== NEXT OBJECT after Kisbox items (abs={pos}) ===")
if pos + 88 <= len(map_data):
    obj = pos
    oid   = struct.unpack_from(">I", map_data, obj +  0)[0]
    tile  = struct.unpack_from(">I", map_data, obj +  4)[0]
    frm   = struct.unpack_from(">I", map_data, obj + 32)[0]
    flags = struct.unpack_from(">I", map_data, obj + 36)[0]
    elev  = struct.unpack_from(">I", map_data, obj + 40)[0]
    pid   = struct.unpack_from(">I", map_data, obj + 44)[0]
    inv_c = struct.unpack_from(">I", map_data, obj + 72)[0]
    print(f"  ObjID={oid}  tile={tile}  frm={frm:#010x}  flags={flags:#010x}  "
          f"elev={elev}  pid={pid:#010x}  inv_c={inv_c}")

    # Compare to what RPU has at the same relative position
    if rpu_map and rpu_kb:
        rpu_pos = rpu_kb + 88
        rpu_ic = struct.unpack_from(">I", rpu_map, rpu_kb + 72)[0]
        for _ in range(rpu_ic):
            p2 = rpu_pos + 4
            p_pid = struct.unpack_from(">I", rpu_map, p2 + 44)[0]
            tb2 = (p_pid >> 24) & 0xFF
            st2 = get_subtype(p_pid & 0xFFFFFF) if tb2 == 0 else None
            e2  = ITEM_EXTRA.get(st2, 4) if st2 is not None else (40 if tb2==1 else 0)
            rpu_pos += 4 + 88 + e2
        print(f"\n  RPU: next object after original Kisbox items at abs={rpu_pos}")
        if rpu_pos + 88 <= len(rpu_map):
            obj2 = rpu_pos
            print(f"  RPU next: ObjID={struct.unpack_from('>I',rpu_map,obj2)[0]}  "
                  f"tile={struct.unpack_from('>I',rpu_map,obj2+4)[0]}  "
                  f"pid={struct.unpack_from('>I',rpu_map,obj2+44)[0]:#010x}")
