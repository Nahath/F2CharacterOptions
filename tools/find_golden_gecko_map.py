"""Find the Golden Gecko interior map and Sajag's proto ID on it."""
import struct, zlib, re
from pathlib import Path

def list_all_dat(dat_path):
    entries = {}
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
        entries[name.replace("\\", "/").lower()] = (comp, unc, packed, offset)
    return entries

def read_file(dat_path, entries, internal):
    key = internal.replace("\\", "/").lower()
    if key not in entries:
        return None
    comp, unc, packed, offset = entries[key]
    with open(dat_path, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(packed)
    return zlib.decompress(raw) if comp else raw

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
rpu_path = game / "mods" / "rpu.dat"

entries = list_all_dat(rpu_path)
map_files = sorted(f for f in entries if f.startswith("maps/") and f.endswith(".map"))
klamath_maps = [f for f in map_files if "kl" in f or "kc" in f or "gold" in f or "geck" in f]
print("Klamath-related maps in rpu.dat:")
for m in klamath_maps:
    print(f"  {m}")

# Also search map names for "golden" or "gecko"
print("\nAll KC/KL maps:")
for m in map_files:
    short = m.split("/")[-1]
    if short.startswith("kc") or short.startswith("kl") or short.startswith("kcgg"):
        print(f"  {m}")
