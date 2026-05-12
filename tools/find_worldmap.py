"""Find worldmap files in all dat archives."""
import struct, zlib
from pathlib import Path

def list_dat(dat_path):
    results = []
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1"); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        results.append((name.lower(), comp, offset, packed))
    return results

def read_entry(dat_path, offset, packed, comp):
    with open(dat_path, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(packed)
    return zlib.decompress(raw) if comp else raw

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

for dat_name in ["master.dat", "mods/rpu.dat", "mods/f2mod.dat", "critter.dat"]:
    dat_path = game_root / dat_name
    if not dat_path.exists():
        continue
    entries = list_dat(dat_path)
    wm_entries = [(n, c, o, p) for n, c, o, p in entries if "worldmap" in n]
    if wm_entries:
        print(f"\n{dat_name}:")
        for n, *_ in wm_entries:
            print(f"  {n}")
    else:
        print(f"{dat_name}: no worldmap files")

# Also look for loose worldmap.txt
for p in [
    game_root / "data" / "world" / "worldmap.txt",
    game_root / "data" / "worldmap.txt",
    game_root / "worldmap.txt",
]:
    if p.exists():
        print(f"\nLoose: {p}")
