"""List all files in critter.dat to see actual path format."""
import struct, zlib
from pathlib import Path

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
dat_path = game / "critter.dat"

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

print(f"Total files: {len(files)}")
print("Sample paths (first 10):")
for f in files[:10]:
    print(f"  {f!r}")

# Show proto files specifically
protos = [f for f in files if "pro" in f.lower().split("\\")[-1] or "pro" in f.lower().split("/")[-1]]
print(f"\nFiles with 'pro' in last component: {len(protos)}")
for f in protos[:10]:
    print(f"  {f!r}")
