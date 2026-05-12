"""
Parse kladwtwn.map objects section to find all critter proto IDs.
Also lists files in critter.dat to verify path format.
"""
import struct, zlib
from pathlib import Path

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
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
                fh.seek(offset)
                raw = fh.read(packed)
            return zlib.decompress(raw) if comp else raw
    return None

def list_dat(dat_path):
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    files = []
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1"); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        files.append(name)
    return files

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

# Show first few critter.dat paths so we know the format
print("critter.dat sample paths:")
critter_files = list_dat(game / "critter.dat")
for f in critter_files[:5]:
    print(f"  {f!r}")
print(f"  ... ({len(critter_files)} total)")

# Load kladwtwn.map
data = read_dat(game / "mods" / "rpu.dat", "maps\\kladwtwn.map")
if data is None:
    data = read_dat(game / "master.dat", "maps\\kladwtwn.map")
print(f"\nkladwtwn.map: {len(data)} bytes")

# Parse header
num_local_vars  = struct.unpack_from(">i", data, 32)[0]
num_global_vars = struct.unpack_from(">i", data, 48)[0]

# Skip to scripts section
pos = 236 + num_global_vars * 4 + num_local_vars * 4
pos += 3 * 10000 * 2  # tiles

# Skip scripts section (3 elevations)
for elev in range(3):
    count = struct.unpack_from(">i", data, pos)[0]; pos += 4
    pad = (16 - (count % 16)) % 16
    pos += (count + pad) * 24

print(f"Objects section starts at offset {pos}")

# Parse objects section
# Format: for each elevation:
#   uint32  object_count
#   per object: varies, but PID is at offset 4 from object start (big-endian uint32)
#
# Fallout 2 object base structure (all big-endian):
#  0: flags      uint32
#  4: PID        uint32   <- type in high byte, proto_id in low 24 bits
#  8: CID        int32
# 12: x (tile)   int32
# 16: y (tile)   int32   (often -1)
# 20: sx         int32
# 24: sy         int32
# 28: frame_idx  uint32
# 32: direction  uint32
# 36: FrmID      uint32
# 40: AnimCode   uint32
# 44: ScriptID   int32   (index into map script slots, -1 if none)
# 48: Inventory  uint32
# 52: inv_cap    uint32  (if Inventory > 0)
# For items the structure may differ; critters have extra fields.
#
# We'll read a minimal structure and use PID to identify critters.
# The object size varies, so we can't iterate by fixed size.
# Instead, let's read counts and known fields.

# Actually the Fallout 2 map object format is NOT fixed-size per object.
# Each object has a variable number of inventory items.
# The "safe" approach: parse object by object using the inventory count.
#
# Base object = 64 bytes (fixed header)
# Followed by inventory items (each ~64 bytes + recursion for nested)
# But critters have additional fields after the base.
#
# Let's use a simpler approach: scan for critter PID pattern.
# Critter PID: high byte = 0x01, next 3 bytes = proto_id.
# In big-endian: bytes are [0x01, hi, mid, lo].
# Look for these in the objects section.

import re

critter_pids = set()
obj_data = data[pos:]

# Scan for big-endian uint32 values with high byte = 0x01 at 4-byte aligned offsets
for i in range(0, len(obj_data) - 3, 4):
    b0, b1, b2, b3 = obj_data[i], obj_data[i+1], obj_data[i+2], obj_data[i+3]
    if b0 == 0x01 and b1 == 0x00 and b2 == 0x00:
        pid = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
        proto_id = pid & 0xFFFFFF
        critter_pids.add(proto_id)

print(f"\nAll critter proto IDs (0x01xxxxxx) found in objects section:")
for pid in sorted(critter_pids):
    print(f"  proto_id={pid}  (obj_pid would be {0x1000000 | pid})")
