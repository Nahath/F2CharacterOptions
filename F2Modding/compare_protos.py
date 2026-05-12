"""
Compare vanilla dynamite protos (51, 52) from master.dat
against Super Dynamite protos (534, 535) from loose files.
"""
import struct, zlib, os

MASTER = r"C:\Games\F2Modding\Fallout 2\master.dat"
PROTO_DIR = r"C:\Games\F2Modding\Fallout 2\data\proto\items"

# --- Parse master.dat (DAT2, little-endian) ---
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

def get_from_dat(proto_id):
    key = f"proto\\items\\{proto_id:08d}.pro"
    if key not in dat_files:
        return None
    comp, real_size, packed_size, offset = dat_files[key]
    raw = data[offset:offset+packed_size]
    if comp != 0:
        raw = zlib.decompress(raw)
    return raw

def get_loose(proto_id):
    path = os.path.join(PROTO_DIR, f"{proto_id:08d}.pro")
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return f.read()

# Field layout for item protos (big-endian fields in the proto itself)
FIELDS = [
    (0,  4, 'PID'),
    (4,  4, 'TextID'),
    (8,  4, 'FrmID'),
    (12, 4, 'LightDistance'),
    (16, 4, 'LightIntensity'),
    (20, 4, 'Flags'),
    (24, 4, 'ExtendedFlags'),
    (28, 4, 'ScriptID'),
    (32, 4, 'ItemType'),
    (36, 4, 'Material'),
    (40, 4, 'Size'),
    (44, 4, 'Weight'),
    (48, 4, 'Cost'),
]

ITEM_TYPES = {0:'Armor',1:'Container',2:'Drug',3:'Weapon',4:'Ammo',5:'Misc',6:'Key'}

def read_field(raw, offset, size):
    val = 0
    for i in range(size):
        val = (val << 8) | raw[offset + i]
    # treat as signed 32-bit
    if size == 4 and val >= 0x80000000:
        val -= 0x100000000
    return val

def hex4(v):
    if v < 0:
        v = v & 0xFFFFFFFF
    return f"0x{v:08x}"

def parse(raw):
    result = {}
    for off, sz, name in FIELDS:
        result[name] = read_field(raw, off, sz)
    result['_raw_tail'] = raw[52:].hex()
    return result

pairs = [(51, 534), (52, 535)]
labels = [('Inert dynamite', 'Super Dynamite (inert)'),
          ('Active dynamite', 'Super Dynamite (active)')]

for (van_id, mod_id), (van_label, mod_label) in zip(pairs, labels):
    van_raw = get_from_dat(van_id)
    mod_raw = get_loose(mod_id)

    if van_raw is None:
        print(f"Could not find vanilla proto {van_id} in master.dat")
        print(f"Keys sample: {list(dat_files.keys())[:5]}")
        continue
    if mod_raw is None:
        print(f"Could not find mod proto {mod_id} as loose file")
        continue

    van = parse(van_raw)
    mod = parse(mod_raw)

    print(f"\n{'='*60}")
    print(f"  {van_label} (PID {van_id})  vs  {mod_label} (PID {mod_id})")
    print(f"{'='*60}")
    print(f"  {'Field':<18} {'Vanilla':>14}  {'Mod':>14}  {'Match'}")
    print(f"  {'-'*18} {'-'*14}  {'-'*14}  {'-'*5}")

    for _, _, name in FIELDS:
        v = van[name]
        m = mod[name]
        if name in ('Flags', 'ExtendedFlags', 'ScriptID'):
            vs = hex4(v)
            ms = hex4(m)
        elif name == 'ItemType':
            vs = ITEM_TYPES.get(v, str(v))
            ms = ITEM_TYPES.get(m, str(m))
        else:
            vs = str(v)
            ms = str(m)
        match = 'OK' if v == m else '*** DIFF'
        # Skip PID/TextID — they're expected to differ
        if name in ('PID', 'TextID'):
            match = '(expected)'
        print(f"  {name:<18} {vs:>14}  {ms:>14}  {match}")

    print(f"  {'Tail (hex)':<18} {van['_raw_tail']}  (vanilla)")
    print(f"  {'':18} {mod['_raw_tail']}  (mod)")
    tail_match = 'OK' if van['_raw_tail'] == mod['_raw_tail'] else '*** DIFF'
    print(f"  Tail match: {tail_match}")
