"""Search all .int files in master.dat and rpu.dat for strings like 'swarm' or 'mantis infesting'."""
import struct, zlib
from pathlib import Path

def list_dat(dat_path):
    results = []
    try:
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
            results.append((name, comp, unc, packed, offset))
    except OSError as e:
        print(f"Error reading {dat_path}: {e}")
    return results

def read_entry(dat_path, offset, packed, comp):
    with open(dat_path, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(packed)
    return zlib.decompress(raw) if comp else raw

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

keywords = [b"swarm", b"mantis infesting", b"spore plants"]

for dat_name in ["master.dat", "mods/rpu.dat"]:
    dat_path = game_root / dat_name
    if not dat_path.exists():
        print(f"{dat_name}: not found")
        continue

    entries = list_dat(dat_path)
    scripts = [(n, c, u, p, o) for n, c, u, p, o in entries
               if n.lower().endswith(".int") and "script" in n.lower()]
    print(f"\n{dat_name}: {len(scripts)} .int files in scripts/")

    hits = []
    for name, comp, unc, packed, offset in scripts:
        data = read_entry(dat_path, offset, packed, comp)
        low = data.lower()
        for kw in keywords:
            if kw in low:
                idx = low.find(kw)
                snippet = data[max(0, idx-10):idx+60]
                hits.append((name, kw, snippet))

    if hits:
        for name, kw, snippet in hits:
            print(f"  HIT  {name}: keyword={kw!r}  context={snippet!r}")
    else:
        print(f"  No hits for {[k.decode() for k in keywords]}")
