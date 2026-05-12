"""Parse encounter map files and check their map_script_id against all scripts.lst versions."""
import struct, zlib, re
from pathlib import Path

def list_and_read_dat(dat_path):
    results = {}
    try:
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
            results[name] = (comp, unc, packed, offset)
    except OSError:
        pass
    return results

def read_entry(dat_path, comp, unc, packed, offset):
    with open(dat_path, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(packed)
    return zlib.decompress(raw) if comp else raw

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    entries = list_and_read_dat(dat_path)
    if target in entries:
        comp, unc, packed, offset = entries[target]
        return read_entry(dat_path, comp, unc, packed, offset)
    return None

def load_lst(dat_path, internal="scripts\\scripts.lst"):
    raw = read_dat(dat_path, internal)
    if raw is None:
        return []
    lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    if lines and not lines[-1]:
        lines = lines[:-1]
    return lines

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

master_lst = load_lst(game_root / "master.dat")
rpu_lst    = load_lst(game_root / "mods" / "rpu.dat")
f2mod_lst  = load_lst(game_root / "mods" / "f2mod.dat")

def lookup(lst, idx):
    if idx == -1:
        return "(no script)"
    if 0 <= idx < len(lst):
        return lst[idx].strip()
    return f"OUT_OF_RANGE({idx},len={len(lst)})"

# Look for encounter maps in master.dat
master_entries = list_and_read_dat(game_root / "master.dat")
rpu_entries    = list_and_read_dat(game_root / "mods" / "rpu.dat")

enc_maps = [n for n in master_entries if n.startswith("maps\\") and n.endswith(".map")
            and any(x in n for x in ["encounter", "desert", "mountain", "cavern", "coast"])]

print(f"Found {len(enc_maps)} encounter maps in master.dat")

interesting = []
for map_name in sorted(enc_maps):
    comp, unc, packed, offset = master_entries[map_name]
    data = read_entry(game_root / "master.dat", comp, unc, packed, offset)

    # Parse map header
    # offset 0: version (int32 BE)
    # offset 4: char[16] map filename
    # offset 20: default tile (int32 BE)
    # offset 24: default elevation (int32 BE)
    # offset 28: default orientation (int32 BE)
    # offset 32: num_local_vars (int32 BE)
    # offset 36: map_script_id (int32 BE)
    if len(data) < 40:
        continue
    version = struct.unpack_from(">i", data, 0)[0]
    map_filename = data[4:20].rstrip(b"\x00").decode("latin-1")
    map_script_id = struct.unpack_from(">i", data, 36)[0]

    m_name = lookup(master_lst, map_script_id)
    r_name = lookup(rpu_lst,    map_script_id)
    f_name = lookup(f2mod_lst,  map_script_id)

    changed = m_name != r_name or m_name != f_name
    interesting.append((map_name, map_filename, map_script_id, m_name, r_name, f_name, changed))

for map_name, map_filename, sid, m, r, f, changed in interesting:
    star = " ***" if changed else ""
    print(f"\n  {map_name}")
    print(f"    header_name={map_filename!r}  script_id={sid}")
    print(f"    master: {m!r}")
    print(f"    rpu:    {r!r}")
    print(f"    f2mod:  {f!r}{star}")

# Also check rpu-only maps
rpu_enc_maps = [n for n in rpu_entries if n.startswith("maps\\") and n.endswith(".map")
                and any(x in n for x in ["encounter", "desert", "mountain", "cavern", "coast"])
                and n not in master_entries]
if rpu_enc_maps:
    print(f"\nRPU-only encounter maps: {len(rpu_enc_maps)}")
    for n in sorted(rpu_enc_maps):
        print(f"  {n}")
