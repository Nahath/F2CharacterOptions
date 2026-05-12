"""
Scan vanilla kladwtwn.map for the Kisbox container (proto 63 = PID 0x0000003F).
With 88-byte headers, the PID is at object_start+44.
So scan for 0x0000003F and check if it's at offset +44 of a plausible object.

Also scan for the Kisbox PID in BOTH RPU and vanilla maps.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"
RPU    = GAME / "mods" / "rpu.dat"

PID_KISBOX = 0x0000003F  # Container proto 63
PID_SAJAG  = 0x01000038  # Critter proto 56

# Item type → extra bytes
ITEM_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}
# Scenery subtype → extra
SCENERY_EXTRA = {0: 0, 1: 4, 2: 8, 3: 8, 4: 4, 5: 4, 6: 16}

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


def scan_for_pid(data: bytes, target_pid: int, label: str):
    """Find all positions where target_pid appears at offset +44 within a plausible object."""
    target_bytes = struct.pack(">I", target_pid)
    results = []
    pos = 0
    while True:
        pos = data.find(target_bytes, pos)
        if pos < 0:
            break
        # Check if this is at offset +44 of an object
        obj_start = pos - 44
        if obj_start >= 0 and obj_start + 88 <= len(data):
            elev = struct.unpack_from(">I", data, obj_start + 40)[0]
            tile = struct.unpack_from(">I", data, obj_start +  4)[0]
            inv  = struct.unpack_from(">I", data, obj_start + 72)[0]
            # Plausibility checks
            if elev <= 2 and (tile <= 40000 or tile == 0xFFFFFFFF) and inv <= 500:
                results.append({
                    "abs":       obj_start,
                    "pid_abs":   pos,
                    "elev":      elev,
                    "tile":      tile,
                    "inv_count": inv,
                })
        pos += 1

    print(f"\n=== {label}: occurrences of PID {target_pid:#010x} at offset +44 ===")
    for r in results:
        print(f"  obj_start={r['abs']}  tile={r['tile']}  elev={r['elev']}  inv_count={r['inv_count']}")
    return results


# ── Vanilla ─────────────────────────────────────────────────────────────────────
vanilla = read_dat(MASTER, r"maps\kladwtwn.map")
print(f"Vanilla: {len(vanilla):,} bytes")

kisbox_locs = scan_for_pid(vanilla, PID_KISBOX, "Vanilla: Kisbox (proto 63)")
sajag_locs  = scan_for_pid(vanilla, PID_SAJAG,  "Vanilla: Sajag (proto 56)")

# For each Kisbox candidate, show a bit of its item data
for kb in kisbox_locs:
    obj_start = kb["abs"]
    inv_count = kb["inv_count"]
    print(f"\n  Kisbox at {obj_start}: inv_count={inv_count}")
    if inv_count > 0:
        # Items start at obj_start + 88 + 0 (Container has 0 extra)
        items_pos = obj_start + 88
        for i in range(min(inv_count, 5)):
            if items_pos + 4 + 44 > len(vanilla):
                break
            qty = struct.unpack_from(">I", vanilla, items_pos)[0]
            child_pid = struct.unpack_from(">I", vanilla, items_pos + 4 + 44)[0]
            items_pos += 4  # skip qty
            # consume child object (rough: 88 + extra, no sub-items assumed)
            child_type = (child_pid >> 24) & 0xFF
            child_proto = child_pid & 0xFFFFFF
            child_extra = ITEM_EXTRA.get(child_type, 4) if child_type == 0 else 0
            print(f"    item[{i}]: qty={qty}  pid={child_pid:#010x}  type={child_type}  proto={child_proto}")
            items_pos += 88 + child_extra  # assume no sub-items for display

# ── RPU ────────────────────────────────────────────────────────────────────────
rpu_data = read_dat(RPU, r"maps\kladwtwn.map")
if rpu_data:
    print(f"\nRPU: {len(rpu_data):,} bytes")
    rpu_kisbox = scan_for_pid(rpu_data, PID_KISBOX, "RPU: Kisbox (proto 63)")
    rpu_sajag  = scan_for_pid(rpu_data, PID_SAJAG,  "RPU: Sajag (proto 56)")

    for kb in rpu_kisbox:
        obj_start = kb["abs"]
        inv_count = kb["inv_count"]
        print(f"\n  RPU Kisbox at {obj_start}: inv_count={inv_count}")
        if inv_count > 0:
            items_pos = obj_start + 88
            for i in range(min(inv_count, 3)):
                if items_pos + 4 + 44 > len(rpu_data):
                    break
                qty = struct.unpack_from(">I", rpu_data, items_pos)[0]
                child_pid = struct.unpack_from(">I", rpu_data, items_pos + 4 + 44)[0]
                child_type  = (child_pid >> 24) & 0xFF
                child_proto = child_pid & 0xFFFFFF
                child_extra = ITEM_EXTRA.get(child_type, 4) if child_type == 0 else 0
                items_pos_next = items_pos + 4 + 88 + child_extra
                print(f"    item[{i}]: qty={qty}  pid={child_pid:#010x}  type={child_type}  proto={child_proto}")
                items_pos = items_pos_next
