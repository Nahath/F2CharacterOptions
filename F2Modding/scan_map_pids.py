"""
Scan a Fallout 2 MAP file and report all object PIDs found,
then check which ones are missing as loose proto files or in master.dat.
"""
import struct, os, zlib

MAP_FILE  = r"C:\Games\F2Modding\Fallout 2\data\maps\ARTEMPLE.MAP"
MASTER    = r"C:\Games\F2Modding\Fallout 2\master.dat"
PROTO_DIR_ITEMS   = r"C:\Games\F2Modding\Fallout 2\data\proto\items"
PROTO_DIR_CRITTER = r"C:\Games\F2Modding\Fallout 2\data\proto\critters"

# --- Build master.dat index ---
with open(MASTER, 'rb') as f:
    mdata = f.read()
mlen = len(mdata)
tree_size = struct.unpack_from('<I', mdata, mlen - 8)[0]
pos = mlen - 8 - tree_size
num_files = struct.unpack_from('<I', mdata, pos)[0]; pos += 4
dat_files = set()
for _ in range(num_files):
    nl = struct.unpack_from('<I', mdata, pos)[0]; pos += 4
    name = mdata[pos:pos+nl].decode('ascii', errors='replace').lower(); pos += nl
    pos += 13  # comp(1) + real(4) + packed(4) + offset(4)
    dat_files.add(name)

def proto_exists(pid):
    ptype = (pid >> 24) & 0xFF
    pnum  = pid & 0x00FFFFFF
    if ptype == 0:   subdir, dirname = "items",    PROTO_DIR_ITEMS
    elif ptype == 1: subdir, dirname = "critters",  PROTO_DIR_CRITTER
    else:            subdir = None
    filename = f"{pnum:08d}.pro"
    # Check loose file
    if subdir:
        loose = os.path.join(dirname, filename)
        if os.path.exists(loose):
            return "loose"
    # Check master.dat
    if subdir:
        key = f"proto\\{subdir}\\{filename}"
        if key in dat_files:
            return "master.dat"
    return None

# --- Parse MAP file ---
# MAP header: version(4) + filename(16) + num_local_vars(4) + map_script_id(4)
# + flags(4) + darkness(4) + num_global_vars(4) + map_id(4) + time(4) + padding(44)
# = 4+16+4+4+4+4+4+4+4+44 = 92 bytes header
# Then 3 * elevation data blocks

with open(MAP_FILE, 'rb') as f:
    raw = f.read()

# Header
version     = struct.unpack_from('>I', raw, 0)[0]
num_gl_vars = struct.unpack_from('>I', raw, 40)[0]
num_lc_vars = struct.unpack_from('>I', raw, 20)[0]
num_elevs   = 3

HEADER_SIZE = 92
pos = HEADER_SIZE

# Skip global vars and local vars (each is 4 bytes)
pos += num_gl_vars * 4
pos += num_lc_vars * 4

# Each elevation: tiles (10000 * 4 bytes) then objects
TILE_GRID = 10000

pids_found = {}  # pid -> count

for elev in range(num_elevs):
    # Tile data: 10000 tiles * 4 bytes each
    pos += TILE_GRID * 4

    # Object count for this elevation
    num_objects = struct.unpack_from('>I', raw, pos)[0]; pos += 4

    for _ in range(num_objects):
        # Object structure (96 bytes base + variable):
        # flags(4) + coords(4) + screen_x(4) + screen_y(4) + frm_index(4)
        # + orientation(4) + frm_id(4) + obj_type_pid(4) + ...
        obj_start = pos
        flags    = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        coords   = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        sx       = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        sy       = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        frm_idx  = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        orient   = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        frm_id   = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        pid      = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        cid      = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        light_r  = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        light_i  = struct.unpack_from('>I', raw, pos)[0]; pos += 4
        out_sid  = struct.unpack_from('>I', raw, pos)[0]; pos += 4  # script id on map

        obj_type = (pid >> 24) & 0xFF
        obj_num  = pid & 0x00FFFFFF

        # Type-specific extra data
        extra = 0
        if obj_type == 0:    # Items
            pos += 4  # item type specific 1
            itype = struct.unpack_from('>I', raw, pos)[0]; pos += 4
            if itype == 0: extra = 4      # Armor: extra 4
            elif itype == 1: extra = 4    # Container: extra 4 (actually variable but skip for now)
            elif itype == 2: extra = 12   # Drug
            elif itype == 3: extra = 4    # Weapon
            elif itype == 4: extra = 4    # Ammo
            elif itype == 5: extra = 4    # Misc
            elif itype == 6: extra = 4    # Key
            pos += extra
        elif obj_type == 1:  # Critters
            pos += 40
        elif obj_type == 2:  # Scenery
            pos += 12
        elif obj_type == 3:  # Walls
            pos += 4
        elif obj_type == 4:  # Tiles
            pos += 4
        elif obj_type == 5:  # Misc (including exits)
            pos += 4

        # Inventory (for items/critters)
        if obj_type in (0, 1):
            inv_count = struct.unpack_from('>I', raw, pos)[0]; pos += 4
            for _ in range(inv_count):
                inv_qty = struct.unpack_from('>I', raw, pos)[0]; pos += 4
                # Recurse not needed here — just track the PID
                inv_pid = struct.unpack_from('>I', raw, pos + 28)[0]
                pids_found[inv_pid] = pids_found.get(inv_pid, 0) + inv_qty
                # Skip the inventory object (simplified — just skip 32 bytes minimum)
                # This is approximate; inventory objects can be complex
                pos += 32
                inv_type = (inv_pid >> 24) & 0xFF

        pids_found[pid] = pids_found.get(pid, 0) + 1

print(f"MAP version {version}, found {len(pids_found)} distinct PIDs\n")
print(f"{'PID':<12} {'Type':<10} {'Num':<6} {'Count':<6} {'Source'}")
print("-" * 55)

TYPE_NAMES = {0:'Item', 1:'Critter', 2:'Scenery', 3:'Wall', 4:'Tile', 5:'Misc'}

missing = []
for pid in sorted(pids_found):
    ptype = (pid >> 24) & 0xFF
    pnum  = pid & 0x00FFFFFF
    count = pids_found[pid]
    tname = TYPE_NAMES.get(ptype, f'type{ptype}')
    source = proto_exists(pid)
    if source is None:
        missing.append((pid, ptype, pnum, count))
        src_str = "*** MISSING ***"
    else:
        src_str = source
    print(f"  {pid:<10}  {tname:<10} {pnum:<6} {count:<6} {src_str}")

if missing:
    print(f"\n*** {len(missing)} missing proto(s):")
    for pid, ptype, pnum, count in missing:
        print(f"  PID {pid} (type={ptype}, num={pnum}) — used {count}x on map")
else:
    print("\nAll protos accounted for.")
