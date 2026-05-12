"""
Scan vanilla kladwtwn.map to determine the exact object-record boundaries
starting from Sajag at 169388.

Strategy: try all 4-byte-aligned offsets from +68 to +488 as candidate
"next object after Sajag" starts, and check whether the candidate has:
  - type_byte in {0,1,2,3,4,5}
  - proto_id in 1..2000
  - flags field = 0 or 0xFFFFFFFF (common values)

Also try to identify how many objects are packed in the 488-byte range.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"

SAJAG_START   = 169388
SAJAG_END     = 169388 + 488   # next critter starts at 169876

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
VALID_TYPES = {0, 1, 2, 3, 4, 5}

print("=== Scanning for valid object starts within [Sajag+68 .. Sajag+484] ===")
print(f"{'rel':>5}  {'abs':>7}  {'flags':>10}  {'PID':>10}  type  proto  note")
for rel in range(68, 488, 4):
    abs_pos = SAJAG_START + rel
    if abs_pos + 8 > len(data):
        break
    flags  = struct.unpack_from(">I", data, abs_pos)[0]
    pid    = struct.unpack_from(">I", data, abs_pos + 4)[0]
    tb     = (pid >> 24) & 0xFF
    proto  = pid & 0xFFFFFF
    if tb not in VALID_TYPES:
        continue
    if not (1 <= proto <= 2000):
        continue
    note = ""
    if flags not in (0, 0xFFFFFFFF, 1, 2, 4):
        note = f" (unusual flags={flags:#010x})"
    print(f"  {rel:5d}  {abs_pos:7d}  {flags:#010x}  {pid:#010x}  {tb:4d}  {proto:5d}  {note}")

# Also check what immediately follows SAJAG_END (= next critter at 169876)
print(f"\n=== Verified: next object at Sajag+488 ===")
abs_pos = SAJAG_END
flags = struct.unpack_from(">I", data, abs_pos)[0]
pid   = struct.unpack_from(">I", data, abs_pos + 4)[0]
print(f"  flags={flags:#010x}  PID={pid:#010x}  type={(pid>>24)&0xFF}  proto={pid&0xFFFFFF}")

# Scan 20 bytes before Sajag to see pattern
print(f"\n=== Context: 20 bytes before Sajag (last object in section?) ===")
for rel in range(-5*4, 4, 4):
    abs_pos = SAJAG_START + rel
    v = struct.unpack_from(">I", data, abs_pos)[0]
    print(f"  {rel:+5d}  abs={abs_pos}  {v:#010x}")

print(f"\n=== First 8 bytes of region starting at key PID candidates ===")
candidates = [72, 140, 188, 232, 280]  # offsets where PIDs were spotted
for rel in candidates:
    abs_pos = SAJAG_START + rel
    flags = struct.unpack_from(">I", data, abs_pos)[0]
    pid   = struct.unpack_from(">I", data, abs_pos + 4)[0]
    tile  = struct.unpack_from(">I", data, abs_pos + 12)[0] if abs_pos+16 <= len(data) else -1
    print(f"  +{rel}: flags={flags:#010x}  PID={pid:#010x}  tile={tile:#010x}")
