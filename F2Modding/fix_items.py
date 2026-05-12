import struct, os

data_dir = "C:/Games/F2Modding/Fallout 2/data/"

# --- Fix 1: create placeholder 00000533.pro ---
# Copy structure from 00000534.pro but with PID 533 and a harmless msg id.
with open(data_dir + "proto/items/00000534.pro", "rb") as f:
    proto = bytearray(f.read())

# Patch PID at offset 0 to 533 (big-endian)
struct.pack_into(">I", proto, 0, 533)
# Patch msg id at offset 4 to 53300
struct.pack_into(">I", proto, 4, 53300)

with open(data_dir + "proto/items/00000533.pro", "wb") as f:
    f.write(proto)
print("Created 00000533.pro as placeholder")

# --- Fix 2: check what ground-items index 0x016F resolves to ---
# The dynamite timer dialog image seems to use the inv_fid's lower 2 bytes
# as an index into the ground items art list. Let's see what's at that index
# and what index vanilla dynamite (inv_fid=0x0700002E, low=0x2E=46) maps to.

import zlib

def extract(dat_path, target):
    with open(dat_path, "rb") as f:
        f.seek(-8, 2)
        ts, _ = struct.unpack("<II", f.read(8))
        tot = f.seek(0, 2)
        f.seek(tot - ts - 8)
        n = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            nl = struct.unpack("<I", f.read(4))[0]
            name = f.read(nl).decode("latin-1")
            comp, rs, ps, off = struct.unpack("<BIII", f.read(13))
            if name.lower().replace("/", "\\") == target.lower():
                f.seek(off); raw = f.read(ps)
                if comp == 1: raw = zlib.decompress(raw)
                return raw
    return None

# Ground items art list
items_lst = extract("C:/Games/F2Modding/Fallout 2/master.dat", "art\\items\\items.lst")
if items_lst:
    lines = [l.strip() for l in items_lst.decode("latin-1").splitlines() if l.strip()]
    print(f"\nGround items.lst has {len(lines)} entries")
    vanilla_idx = 0x2E   # vanilla dynamite inv_fid lower bytes
    our_idx     = 0x016F  # our inv_fid lower bytes
    print(f"  Index 0x{vanilla_idx:02X}={vanilla_idx}: {lines[vanilla_idx] if vanilla_idx < len(lines) else 'OUT OF RANGE'}")
    print(f"  Index 0x{our_idx:03X}={our_idx}: {lines[our_idx] if our_idx < len(lines) else 'OUT OF RANGE'}")

    # Also find the dynamite and grenade entries by name
    for i, l in enumerate(lines):
        if any(x in l.lower() for x in ["dynam", "grenad"]):
            print(f"  index {i}: {l}")
