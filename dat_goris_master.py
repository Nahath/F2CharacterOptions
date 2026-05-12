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

master = 'C:/Program Files (x86)/GOG Galaxy/Games/Fallout 2/master.dat'

goris_ids = [152, 319, 320, 321, 322, 323, 324]
print('=== Goris proto body type in master.dat ===')
for pid in goris_ids:
    fname = 'proto\\critters\\%08d.pro' % pid
    data = read_from_dat(master, fname)
    if data is None:
        print('%s: NOT FOUND in master.dat' % fname)
    else:
        if len(data) >= 392:
            body_type = struct.unpack_from('>I', data, 388)[0]
            label = 'Biped' if body_type == 0 else 'Quadruped' if body_type == 1 else 'Unknown(%d)' % body_type
            print('%s: FOUND, len=%d, PROTO_CR_BODY_TYPE at offset 388 = %d (%s)' % (fname, len(data), body_type, label))
        else:
            print('%s: FOUND but too short (len=%d)' % (fname, len(data)))

# Also check scripts.lst in master.dat for dynamite
print()
print('=== scripts.lst in master.dat for dynam ===')
data_sl = read_from_dat(master, 'scripts\\scripts.lst')
if data_sl:
    text = data_sl.decode('latin-1')
    for i, line in enumerate(text.splitlines(), 1):
        if 'dynam' in line.lower():
            print('Line %d: %s' % (i, line))
else:
    print('scripts.lst not found in master.dat')
