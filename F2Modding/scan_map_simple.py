"""
Simple binary scan of ARTEMPLE.MAP for item PIDs.
Searches for all 4-byte big-endian values in known item PID ranges
and reports whether each has a proto file available.
"""
import struct, os

MAP_FILE  = r"C:\Games\F2Modding\Fallout 2\data\maps\ARTEMPLE.MAP"
MASTER    = r"C:\Games\F2Modding\Fallout 2\master.dat"
PROTO_DIR = r"C:\Games\F2Modding\Fallout 2\data\proto\items"

# Build master.dat index
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
    pos += 13
    dat_files.add(name)

def item_proto_exists(num):
    filename = f"{num:08d}.pro"
    loose = os.path.join(PROTO_DIR, filename)
    if os.path.exists(loose):
        return "loose"
    key = f"proto\\items\\{filename}"
    if key in dat_files:
        return "master.dat"
    return None

with open(MAP_FILE, 'rb') as f:
    raw = f.read()

print(f"Map size: {len(raw)} bytes")
print(f"Scanning for item PIDs (type=0x00, num 1-600)...\n")

found = {}
for i in range(0, len(raw) - 3):
    val = struct.unpack_from('>I', raw, i)[0]
    ptype = (val >> 24) & 0xFF
    pnum  = val & 0x00FFFFFF
    if ptype == 0 and 1 <= pnum <= 600:
        found[pnum] = found.get(pnum, 0) + 1

print(f"{'Item PID':<12} {'Occurrences':<14} {'Proto source'}")
print("-" * 45)
missing = []
for pnum in sorted(found):
    count = found[pnum]
    source = item_proto_exists(pnum)
    src_str = source if source else "*** MISSING ***"
    print(f"  {pnum:<12} {count:<14} {src_str}")
    if not source:
        missing.append(pnum)

print()
if missing:
    print(f"MISSING protos: {missing}")
else:
    print("All item PIDs found in proto sources.")
