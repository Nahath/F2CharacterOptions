"""Scan entire kladwtwn.map for all critter PID occurrences (not just aligned)."""
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

# Search for PID 56 bytes: 0x01, 0x00, 0x00, 0x38
pid56 = bytes([0x01, 0x00, 0x00, 0x38])
pos = 0
found56 = []
while True:
    idx = data.find(pid56, pos)
    if idx == -1:
        break
    found56.append(idx)
    pos = idx + 1

print(f"Proto 56 PID (01 00 00 38) occurrences: {len(found56)}")
for off in found56:
    print(f"  offset {off} (aligned: {off % 4 == 0})")

# Also search for RPU-common alternative PIDs that might be Sajag
# If sajag was renumbered in RPU, look for script kcsajag reference instead
# Let's scan for all critter PIDs in entire file (any alignment)
from collections import Counter
pids = Counter()
for i in range(len(data) - 3):
    b = data[i:i+4]
    if b[0] == 0x01 and b[1] == 0x00 and b[2] == 0x00:
        pids[b[3]] += 1

print("\nAll critter proto IDs (01 00 00 XX) found anywhere in file:")
for proto_id, count in sorted(pids.items()):
    print(f"  proto_id={proto_id}  count={count}")
