import struct, zlib

def read_from_dat(dat_path, internal_path):
    target = internal_path.lower().replace('/', '\\')
    with open(dat_path, 'rb') as f:
        f.seek(-8, 2)
        tree_size, dat_size = struct.unpack('<II', f.read(8))
        f.seek(dat_size - tree_size - 8)
        tree = f.read(tree_size)
    pos = 4
    while pos < len(tree):
        name_len = struct.unpack_from('<I', tree, pos)[0]; pos += 4
        name = tree[pos:pos+name_len].decode('latin-1'); pos += name_len
        compression = tree[pos]; pos += 1
        usz, psz, off = struct.unpack_from('<III', tree, pos); pos += 12
        if name.lower() == target:
            with open(dat_path, 'rb') as f:
                f.seek(off); raw = f.read(psz)
            return zlib.decompress(raw) if compression else raw
    return None

def list_dat(dat_path, prefix=''):
    prefix_norm = prefix.lower().replace('/', '\\')
    with open(dat_path, 'rb') as f:
        f.seek(-8, 2)
        tree_size, dat_size = struct.unpack('<II', f.read(8))
        f.seek(dat_size - tree_size - 8)
        tree = f.read(tree_size)
    pos = 4
    files = []
    while pos < len(tree):
        name_len = struct.unpack_from('<I', tree, pos)[0]; pos += 4
        name = tree[pos:pos+name_len].decode('latin-1'); pos += name_len
        compression = tree[pos]; pos += 1
        usz, psz, off = struct.unpack_from('<III', tree, pos); pos += 12
        if name.lower().startswith(prefix_norm):
            files.append(name)
    return files

rpu = 'C:/Program Files (x86)/GOG Galaxy/Games/Fallout 2/mods/rpu.dat'
master = 'C:/Program Files (x86)/GOG Galaxy/Games/Fallout 2/master.dat'

# ====== TASK 1: rpu.dat critter protos ======
critter_files = list_dat(rpu, 'proto\\critters\\')
print('=== proto\\critters\\ files in rpu.dat ===')
for f in sorted(critter_files):
    print(f)
print(f'Total: {len(critter_files)}')

goris_ids = [152, 319, 320, 321, 322, 323, 324]
print()
print('=== Goris proto body type checks ===')
for pid in goris_ids:
    fname = 'proto\\critters\\%08d.pro' % pid
    data = read_from_dat(rpu, fname)
    if data is None:
        print('%s: NOT FOUND in rpu.dat' % fname)
    else:
        if len(data) >= 392:
            body_type = struct.unpack_from('>I', data, 388)[0]
            label = 'Biped' if body_type == 0 else 'Quadruped' if body_type == 1 else 'Unknown(%d)' % body_type
            print('%s: FOUND, len=%d, PROTO_CR_BODY_TYPE at offset 388 = %d (%s)' % (fname, len(data), body_type, label))
        else:
            print('%s: FOUND but too short (len=%d)' % (fname, len(data)))

# ====== TASK 2: master.dat item protos ======
print()
print('=== proto\\items\\00000085.pro ===')
data85 = read_from_dat(master, 'proto\\items\\00000085.pro')
if data85 is None:
    print('NOT FOUND')
else:
    print('len=%d' % len(data85))
    pid = struct.unpack_from('>I', data85, 0)[0]
    script_id = struct.unpack_from('>i', data85, 28)[0]
    item_type = struct.unpack_from('>I', data85, 32)[0]
    print('  PID (offset 0, uint32 BE): %d (0x%08X)' % (pid, pid))
    print('  ScriptID (offset 28, int32 BE): %d' % script_id)
    print('  ItemType (offset 32, uint32 BE): %d' % item_type)

print()
print('=== proto\\items\\00000050.pro ===')
data50 = read_from_dat(master, 'proto\\items\\00000050.pro')
if data50 is None:
    print('NOT FOUND')
else:
    print('len=%d' % len(data50))
    pid = struct.unpack_from('>I', data50, 0)[0]
    script_id = struct.unpack_from('>i', data50, 28)[0]
    item_type = struct.unpack_from('>I', data50, 32)[0]
    print('  PID (offset 0, uint32 BE): %d (0x%08X)' % (pid, pid))
    print('  ScriptID (offset 28, int32 BE): %d' % script_id)
    print('  ItemType (offset 32, uint32 BE): %d' % item_type)

# ====== TASK 2b: scripts.lst ======
print()
print('=== scripts.lst lines containing "dynam" (case-insensitive) ===')
spath = 'C:/Program Files (x86)/GOG Galaxy/Games/Fallout 2/data/scripts/scripts.lst'
with open(spath, 'r', encoding='latin-1') as f:
    lines = f.readlines()
found = False
for i, line in enumerate(lines, 1):
    if 'dynam' in line.lower():
        print('Line %d: %s' % (i, line.rstrip()))
        found = True
if not found:
    print('(no matches)')
