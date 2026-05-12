"""Debug the objects section start for vanilla kladwtwn.map."""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
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
    return None

data = read_dat(MASTER, r"maps\kladwtwn.map")
print(f"Map size: {len(data):,} bytes")

# Dump from supposed OBJ_START
OBJ_START = 60324
print(f"\n=== Bytes at OBJ_START={OBJ_START} ===")
for i in range(0, 80, 4):
    v = struct.unpack_from(">I", data, OBJ_START + i)[0]
    note = ""
    if i == 0: note = "<-- total count?"
    if i == 4: note = "<-- elevation 0 count?"
    if i == 8: note = "<-- elevation 1 count?"
    if i == 12: note = "<-- elevation 2 count?"
    print(f"  +{i:3d}  {v:#010x} = {v:10d}  {note}")

# Try reading as: total_count(4) then 3 elevation counts(4 each)
total = struct.unpack_from(">I", data, OBJ_START)[0]
print(f"\ntotal_count = {total}")
for elev in range(3):
    cnt = struct.unpack_from(">I", data, OBJ_START + 4 + elev*4)[0]
    print(f"  elevation {elev} count = {cnt}")

# Try without total_count: first 4 bytes = elevation 0 count
print(f"\n--- Without total_count header ---")
for elev in range(3):
    cnt = struct.unpack_from(">I", data, OBJ_START + elev*4)[0]
    print(f"  elevation {elev} count = {cnt}")

# Scan for first valid object (PID at +44 with type in {0,1,2})
print(f"\n=== Scanning for valid objects at OBJ_START ===")
# Try to find where first valid PID appears at offset multiples of 4
# starting from OBJ_START + 4 or + 16
VALID_TYPES = {0,1,2,3,4,5}
for skip in range(0, 20, 4):
    pos = OBJ_START + skip
    # If counts are at start, first object at pos
    # Check if there's a valid PID at pos+44
    v44 = struct.unpack_from(">I", data, pos + 44)[0]
    tb  = (v44 >> 24) & 0xFF
    pr  = v44 & 0xFFFFFF
    if tb in VALID_TYPES and 1 <= pr <= 2000:
        print(f"  skip={skip}: PID candidate at +44 = {v44:#010x} type={tb} proto={pr}")

# What's right before OBJ_START?
print(f"\n=== Context before OBJ_START ===")
for i in range(-5*4, 4, 4):
    v = struct.unpack_from(">I", data, OBJ_START + i)[0]
    print(f"  {OBJ_START+i} (+{i:+4d}):  {v:#010x} = {v:10d}")

# Check scripts section to confirm OBJ_START
# scripts_start is supposed to be at 60312 for vanilla
scripts_start = 60312
print(f"\n=== Scripts section at {scripts_start} ===")
print(f"5 group counts:")
for g in range(5):
    cnt = struct.unpack_from(">I", data, scripts_start + g*4)[0]
    print(f"  group {g}: {cnt}")
total_scripts_size = 20  # 5 × 4 bytes for zero counts
print(f"=> OBJ_START = {scripts_start + total_scripts_size}")

# Also check vanilla MAP header to find scripts_start
print(f"\n=== MAP header analysis ===")
# Standard Fallout 2 MAP header layout:
# 0: version (4)
# 4: map_name (16 chars? or string?)
# ... complex layout, let's just check the scripts section
# For vanilla kladwtwn.map, scripts_start was empirically 60312
# = 4 (version) + ... + tile_data...
# Tile data = 30000 tiles × 4 bytes (?)
# No wait: 60000 bytes of tile data (2 bytes/tile × 30000)?
# Header ends at 232 or 236?

# Let's look at the section boundary search approach
# Tile data in F2 MAP: 100×100 = 10000 tiles per level, 3 levels = 30000 tiles
# Each tile = 2×int16 (floors + walls) = 4 bytes → 30000 × 4 = 120000 bytes?
# But scripts_start at 60312 seems small for that...
# Maybe only 1 level of tiles? 10000 × 4 = 40000? Still not 60312...
# Or 30000 tiles × 2 bytes = 60000 + header ~312?
print(f"scripts_start={scripts_start}")
print(f"header_size = {scripts_start - 60000} bytes (if tile_data=60000)")
