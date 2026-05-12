"""Parse Fallout 2 map file, extract all spatial/timed script objects and their ScriptIDs,
then look up those IDs in master.dat and rpu.dat scripts.lst to see what names they map to."""
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

def read_scripts_lst(dat_path, internal="scripts\\scripts.lst"):
    raw = read_dat(dat_path, internal)
    if raw is None:
        return []
    lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    if lines and not lines[-1]:
        lines = lines[:-1]
    return lines

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

# Load arvillag.map from master.dat
map_data = read_dat(game_root / "master.dat", "maps\\arvillag.map")
if map_data is None:
    map_data = read_dat(game_root / "mods" / "rpu.dat", "maps\\arvillag.map")
    src = "rpu.dat"
else:
    src = "master.dat"

print(f"arvillag.map from {src}: {len(map_data)} bytes")

# Load scripts.lst from multiple sources
master_lst = read_scripts_lst(game_root / "master.dat")
rpu_lst    = read_scripts_lst(game_root / "mods" / "rpu.dat")
f2mod_lst  = read_scripts_lst(game_root / "mods" / "f2mod.dat")

print(f"master.dat scripts.lst: {len(master_lst)} entries")
print(f"rpu.dat    scripts.lst: {len(rpu_lst)} entries")
print(f"f2mod.dat  scripts.lst: {len(f2mod_lst)} entries")

# ── Fallout 2 map format ──────────────────────────────────────────────────────
# Header: 4 bytes version, then fields
# Map header is big-endian
# Offset 0:   int32 version
# Offset 4:   char[16] map name
# Offset 20:  int32 default player start tile
# Offset 24:  int32 default elevation
# Offset 28:  int32 default orientation
# Offset 32:  int32 num local vars
# Offset 36:  int32 script_id (index into scripts.lst; map-level script)
# Offset 40:  int32 flags
# Offset 44:  int32 darkness
# Offset 48:  int32 num global vars
# Offset 52:  int32 map_id
# Offset 56:  int32 ticks
# Offset 60:  int32[44] reserved
# Header total = 60 + 44*4 = 236 bytes

pos = 0
version = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
map_name = map_data[pos:pos+16].rstrip(b"\x00").decode("latin-1"); pos += 16
default_tile = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
default_elev = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
default_orient = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
num_local_vars = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
map_script_id = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
flags = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
darkness = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
num_global_vars = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
map_id = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
ticks = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
pos += 44 * 4  # reserved
# pos should now be 236

print(f"\nMap header:")
print(f"  version={version}, name={map_name!r}, script_id={map_script_id}")
print(f"  local_vars={num_local_vars}, global_vars={num_global_vars}")
if map_script_id >= 0:
    def lookup(lst, idx):
        return lst[idx].strip() if 0 <= idx < len(lst) else f"OUT_OF_RANGE({idx})"
    print(f"  Map script -> master: {lookup(master_lst, map_script_id)}")
    print(f"  Map script -> rpu:    {lookup(rpu_lst,    map_script_id)}")
    print(f"  Map script -> f2mod:  {lookup(f2mod_lst,  map_script_id)}")

# ── Global/local variable space ───────────────────────────────────────────────
# After header: global vars, then local vars (all int32 BE)
pos += num_global_vars * 4
pos += num_local_vars  * 4

# ── Tiles (3 elevations × 10000 tiles × 2 bytes) ────────────────────────────
# Actually each tile entry = 2 bytes (roof + floor)
# 3 elevations × 100×100 = 30000 tile entries × 2 bytes each = 60000 bytes
pos += 3 * 10000 * 2  # tile section

print(f"\nScripts section starts at offset: {pos}")

# ── Scripts section ───────────────────────────────────────────────────────────
# Each elevation has a script list
# Format: int32 script_count, then for each: 16-byte script record
# Script record:
#   int32  pid           (script type in high byte, index in low 24 bits)
#   int32  next          (linked list)
#   int16  script_loops  (for timed)
#   int16  script_timer  (for timed)
#   int32  flags
#   int32  script_idx    (0-based scripts.lst index, or -1)
#   int32  dummy[4]      (unknown fields, varies by type)
# Actually the exact layout varies — let's try to parse cautiously

spatial_scripts = []
timed_scripts   = []

for elev in range(3):
    script_count = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
    print(f"\nElevation {elev}: {script_count} scripts at data offset {pos}")

    for i in range(script_count):
        if pos + 16 > len(map_data):
            print(f"  TRUNCATED at script {i}")
            break
        # PID: high byte = type (0=none,1=spatial,2=timed,3=item,4=critter,5=entrance)
        pid = struct.unpack_from(">i", map_data, pos)[0]
        script_type = (pid >> 24) & 0xFF
        script_idx  = pid & 0x00FFFFFF
        pos += 4

        # next ptr
        nxt = struct.unpack_from(">i", map_data, pos)[0]; pos += 4

        if script_type == 1:  # Spatial
            # tile_num (int32) + unused (int32) + flags (int32) + script_id (int32)
            tile   = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            unused = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            sflags = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            sid    = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            spatial_scripts.append((elev, i, tile, sid))
        elif script_type == 2:  # Timed
            time   = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            unused = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            sflags = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            sid    = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            timed_scripts.append((elev, i, time, sid))
        else:
            # other types: read 4 int32 fields generically
            f1 = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            f2 = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            f3 = struct.unpack_from(">i", map_data, pos)[0]; pos += 4
            sid = struct.unpack_from(">i", map_data, pos)[0]; pos += 4

    # After scripts, there's a padding to align to 16 records
    # (pad so total is multiple of 16)
    pad_count = (16 - (script_count % 16)) % 16
    if pad_count > 0:
        pos += pad_count * (4 + 4 + 4*4)  # each padded record = 24 bytes

print(f"\n=== Spatial scripts ({len(spatial_scripts)} total) ===")
unique_sids = set()
for elev, i, tile, sid in spatial_scripts:
    unique_sids.add(sid)

for sid in sorted(unique_sids):
    if sid == -1:
        print(f"  ScriptID=-1 (no script)")
        continue
    m = master_lst[sid].strip() if 0 <= sid < len(master_lst) else f"RANGE({len(master_lst)})"
    r = rpu_lst[sid].strip()    if 0 <= sid < len(rpu_lst)    else f"RANGE({len(rpu_lst)})"
    f = f2mod_lst[sid].strip()  if 0 <= sid < len(f2mod_lst)  else f"RANGE({len(f2mod_lst)})"
    print(f"  ScriptID={sid:4d}  master={m!r:40s}  rpu={r!r:40s}  f2mod={f!r}")

print(f"\n=== Timed scripts ({len(timed_scripts)} total) ===")
unique_tids = set()
for elev, i, time, sid in timed_scripts:
    unique_tids.add(sid)
for sid in sorted(unique_tids):
    if sid == -1:
        print(f"  ScriptID=-1")
        continue
    m = master_lst[sid].strip() if 0 <= sid < len(master_lst) else f"RANGE({len(master_lst)})"
    r = rpu_lst[sid].strip()    if 0 <= sid < len(rpu_lst)    else f"RANGE({len(rpu_lst)})"
    f = f2mod_lst[sid].strip()  if 0 <= sid < len(f2mod_lst)  else f"RANGE({len(f2mod_lst)})"
    print(f"  ScriptID={sid:4d}  master={m!r:40s}  rpu={r!r:40s}  f2mod={f!r}")
