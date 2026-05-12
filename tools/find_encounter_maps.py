"""Find encounter maps for ARRO area and check their map scripts."""
import struct, zlib, re
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
        results.append((name.lower(), comp, unc, packed, offset))
    return results

def read_entry(dat_path, offset, packed, comp):
    with open(dat_path, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(packed)
    return zlib.decompress(raw) if comp else raw

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

# Load scripts.lst versions
def load_scripts_lst(dat_path, internal="scripts\\scripts.lst"):
    raw = read_dat(dat_path, internal)
    if raw is None:
        return []
    lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    return [l for l in lines if l]  # keep all non-empty

master_lst = load_scripts_lst(game_root / "master.dat")
rpu_lst    = load_scripts_lst(game_root / "mods" / "rpu.dat")

# Find all maps with "arro" or "sp" prefix (spore/arroyo encounters)
for dat_name in ["master.dat", "mods/rpu.dat"]:
    dat_path = game_root / dat_name
    if not dat_path.exists():
        continue
    entries = list_dat(dat_path)
    maps = [(n, c, u, p, o) for n, c, u, p, o in entries
            if n.endswith(".map") and "maps" in n]

    arro_maps = [(n, c, u, p, o) for n, c, u, p, o in maps
                 if any(x in n for x in ["arro", "sp", "mantis", "swarm", "spore"])]

    print(f"\n{dat_name} — maps matching arro/sp/mantis/swarm/spore:")
    for name, *_ in arro_maps:
        print(f"  {name}")

    if not arro_maps:
        print("  (none)")

# Now look at worldmap.txt (from rpu.dat) for ARRO area encounter definitions
print("\n=== worldmap.txt ARRO section (rpu.dat) ===")
wm = read_dat(game_root / "mods" / "rpu.dat", "data\\world\\worldmap.txt")
if wm is None:
    wm = read_dat(game_root / "master.dat", "data\\world\\worldmap.txt")
    src = "master.dat"
else:
    src = "rpu.dat"

if wm:
    text = wm.decode("latin-1")
    # Find ARRO encounter group sections
    lines = text.split("\n")
    in_arro = False
    for i, line in enumerate(lines):
        if "ARRO_Spore" in line or "Spore_Plant" in line:
            # Print surrounding context
            start = max(0, i - 2)
            end = min(len(lines), i + 20)
            print(f"\n  Context around line {i}:")
            for j in range(start, end):
                print(f"    {j:4d}: {lines[j]}")
