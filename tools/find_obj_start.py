"""Dump bytes around the expected objects section start to find the real format."""
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

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
data = read_dat(game / "mods" / "rpu.dat", "maps\\kladwtwn.map")

# Show scripts section counts per elevation so we can trust the objects start
num_local_vars  = struct.unpack_from(">i", data, 32)[0]
num_global_vars = struct.unpack_from(">i", data, 48)[0]
pos = 236 + num_global_vars * 4 + num_local_vars * 4 + 3 * 10000 * 2
print(f"Scripts section starts at: {pos}")
for elev in range(3):
    count = struct.unpack_from(">i", data, pos)[0]
    pad = (16 - (count % 16)) % 16
    print(f"  Elevation {elev}: count={count}  pad={pad}  section_bytes={4 + (count+pad)*24}")
    pos += 4 + (count + pad) * 24
print(f"Objects section starts at: {pos}")

# Dump 120 bytes starting from objects section in 4-byte groups
print(f"\nFirst 120 bytes at {pos} (objects section):")
for i in range(0, 120, 4):
    val = struct.unpack_from(">I", data, pos + i)[0]
    ival = struct.unpack_from(">i", data, pos + i)[0]
    print(f"  +{i:3d}: {val:#010x}  ({ival:12d})")

# Also check if there's a total-objects header before elevation counts
# by showing bytes before pos
print(f"\n4 bytes just before objects section ({pos-4}):")
val = struct.unpack_from(">I", data, pos - 4)[0]
print(f"  {val:#010x}  ({struct.unpack_from('>i', data, pos-4)[0]})")
