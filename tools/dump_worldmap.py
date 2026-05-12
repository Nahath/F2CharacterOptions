"""Dump worldmap.txt sections relevant to Arroyo/spore/mantis encounters."""
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

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

for dat_name in ["mods/rpu.dat", "master.dat"]:
    dat_path = game_root / dat_name
    if not dat_path.exists():
        continue
    wm = read_dat(dat_path, "data\\world\\worldmap.txt")
    if wm is None:
        print(f"{dat_name}: worldmap.txt not found")
        continue

    text = wm.decode("latin-1")
    lines = text.split("\n")
    print(f"\n=== worldmap.txt from {dat_name} ({len(lines)} lines) ===")

    # Find ALL lines with 'Script=' keyword
    print("\nAll 'Script=' entries:")
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("script="):
            print(f"  {i:5d}: {line.rstrip()}")

    # Find 'arro', 'spore', 'mantis', 'swarm' mentions
    print("\nLines with arro/spore/mantis/swarm:")
    for i, line in enumerate(lines):
        l = line.lower()
        if any(kw in l for kw in ["arro", "spore", "mantis", "swarm"]):
            print(f"  {i:5d}: {line.rstrip()}")

    break  # only need one source
