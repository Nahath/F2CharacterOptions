"""
Recreate Super Dynamite proto files 534 and 535 from scratch,
derived from vanilla dynamite protos 51 and 52 in master.dat.
"""
import struct, zlib, os

MASTER = r"C:\Games\F2Modding\Fallout 2\master.dat"
PROTO_DIR = r"C:\Games\F2Modding\Fallout 2\data\proto\items"

# --- Parse master.dat ---
with open(MASTER, 'rb') as f:
    data = f.read()

file_size = len(data)
tree_size = struct.unpack_from('<I', data, file_size - 8)[0]
tree_start = file_size - 8 - tree_size
pos = tree_start
num_files = struct.unpack_from('<I', data, pos)[0]; pos += 4

dat_files = {}
for _ in range(num_files):
    nl = struct.unpack_from('<I', data, pos)[0]; pos += 4
    name = data[pos:pos+nl].decode('ascii', errors='replace'); pos += nl
    comp = data[pos]; pos += 1
    real_size = struct.unpack_from('<I', data, pos)[0]; pos += 4
    packed_size = struct.unpack_from('<I', data, pos)[0]; pos += 4
    offset = struct.unpack_from('<I', data, pos)[0]; pos += 4
    dat_files[name.lower()] = (comp, real_size, packed_size, offset)

def get_vanilla(proto_id):
    key = f"proto\\items\\{proto_id:08d}.pro"
    if key not in dat_files:
        raise FileNotFoundError(f"Proto {proto_id} not found in master.dat (key: {key})")
    comp, real_size, packed_size, offset = dat_files[key]
    raw = data[offset:offset+packed_size]
    if comp != 0:
        raw = zlib.decompress(raw)
    return bytearray(raw)

def write_be32(ba, offset, value):
    struct.pack_into('>I', ba, offset, value & 0xFFFFFFFF)

# Build proto 534: vanilla 51 with PID=534, TextID=53400, FrmID=23 (keep as-is)
proto534 = get_vanilla(51)
write_be32(proto534, 0,  534)    # PID
write_be32(proto534, 4,  53400)  # TextID
# FrmID stays 23 (same as vanilla inert) - user controls this
out534 = os.path.join(PROTO_DIR, "00000534.pro")
with open(out534, 'wb') as f:
    f.write(proto534)
print(f"Written {out534} ({len(proto534)} bytes)")

# Build proto 535: vanilla 52 with PID=535, TextID=53500, FrmID=23 (user wants same icon)
proto535 = get_vanilla(52)
write_be32(proto535, 0,  535)    # PID
write_be32(proto535, 4,  53500)  # TextID
write_be32(proto535, 8,  23)     # FrmID: set to 23 to match inert (user's intent)
out535 = os.path.join(PROTO_DIR, "00000535.pro")
with open(out535, 'wb') as f:
    f.write(proto535)
print(f"Written {out535} ({len(proto535)} bytes)")

print("\nVerifying...")
for path, label in [(out534, "534"), (out535, "535")]:
    ba = bytearray(open(path,'rb').read())
    pid = struct.unpack_from('>I', ba, 0)[0]
    tid = struct.unpack_from('>I', ba, 4)[0]
    frm = struct.unpack_from('>I', ba, 8)[0]
    wgt = struct.unpack_from('>I', ba, 44)[0]
    cst = struct.unpack_from('>I', ba, 48)[0]
    print(f"  Proto {label}: PID={pid} TextID={tid} FrmID={frm} Weight={wgt} Cost={cst}")
