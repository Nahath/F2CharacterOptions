"""Dump full encounter sections from worldmap.txt and show what's at script IDs 610-620 in each scripts.lst."""
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

# Load scripts.lst from each source
def load_lst(dat_path, internal="scripts\\scripts.lst"):
    raw = read_dat(dat_path, internal)
    if raw is None:
        return []
    lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    if lines and not lines[-1]:
        lines = lines[:-1]
    return lines

master_lst = load_lst(game_root / "master.dat")
rpu_lst    = load_lst(game_root / "mods" / "rpu.dat")
f2mod_lst  = load_lst(game_root / "mods" / "f2mod.dat")

# Show script IDs 610-620 in each list (neighborhood of 614)
print("=== scripts.lst entries around index 614 ===")
for idx in range(610, 625):
    m = master_lst[idx].strip() if idx < len(master_lst) else "OUT_OF_RANGE"
    r = rpu_lst[idx].strip()    if idx < len(rpu_lst)    else "OUT_OF_RANGE"
    f = f2mod_lst[idx].strip()  if idx < len(f2mod_lst)  else "OUT_OF_RANGE"
    diff = " *** CHANGED" if m != r else ""
    print(f"  {idx:4d}  master={m!r:50s}  rpu={r!r}{diff}")

print()

# Dump [Encounter: ARRO_Spore_Plants] and nearby sections
wm = read_dat(game_root / "mods" / "rpu.dat", "data\\worldmap.txt")
if wm:
    lines = wm.decode("latin-1").split("\n")
    in_section = False
    for i, line in enumerate(lines):
        if "[Encounter: ARRO_Spore_Plants]" in line:
            in_section = True
        if in_section:
            print(f"{i:5d}: {line.rstrip()}")
            # Stop at next section header
            if i > 311 and line.strip().startswith("["):
                break
        if i > 330:
            break

print()
# Also check for a 'lookup_name' or 'Name=' or 'Description=' field in worldmap.txt
print("=== All Name= / lookup_name= / Description= entries ===")
if wm:
    lines = wm.decode("latin-1").split("\n")
    for i, line in enumerate(lines):
        ls = line.strip().lower()
        if ls.startswith("name=") or ls.startswith("lookup_name") or ls.startswith("description"):
            print(f"  {i:5d}: {line.rstrip()}")
