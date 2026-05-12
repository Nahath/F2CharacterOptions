import struct, zlib, os

data_dir = "C:/Games/F2Modding/Fallout 2/data/proto/items/"
new_pros = ["00000532.pro", "00000534.pro", "00000535.pro"]

# Also extract the real dynamite proto from master.dat for comparison
dat_path = "C:/Games/F2Modding/Fallout 2/master.dat"

def read_dat_file(dat_path, target_suffix):
    with open(dat_path, "rb") as f:
        f.seek(-8, 2)
        tree_size, data_size = struct.unpack("<II", f.read(8))
        total_size = f.seek(0, 2)
        tree_offset = total_size - tree_size - 8
        f.seek(tree_offset)
        num_files = struct.unpack("<I", f.read(4))[0]
        for _ in range(num_files):
            name_len = struct.unpack("<I", f.read(4))[0]
            name = f.read(name_len).decode("latin-1")
            comp, real_size, packed_size, offset = struct.unpack("<BIII", f.read(13))
            if name.lower().endswith(target_suffix.lower()):
                pos = f.tell()
                f.seek(offset)
                data = f.read(packed_size)
                if comp == 1:
                    data = zlib.decompress(data)
                return name, data
    return None, None

def parse_item_pro(data, label):
    if len(data) < 20:
        print(f"{label}: too short ({len(data)} bytes)")
        return
    pid = struct.unpack(">I", data[0:4])[0]
    msg_id = struct.unpack(">I", data[4:8])[0]
    fid = struct.unpack(">I", data[8:12])[0]
    flags = struct.unpack(">I", data[12:16])[0]
    proto_flags = struct.unpack(">I", data[16:20])[0]
    # item type is at offset 44 in item protos
    item_type = struct.unpack(">I", data[44:48])[0] if len(data) >= 48 else -1
    print(f"{label}: size={len(data)}, PID=0x{pid:08X} ({pid & 0xFFFF}), msg={msg_id}, FID=0x{fid:08X}, flags=0x{flags:08X}, proto_flags=0x{proto_flags:08X}, item_type={item_type}")
    print(f"  raw hex: {data.hex()}")

# Find dynamite in master.dat items.lst to get its proto number
name, lst_data = read_dat_file(dat_path, "proto\\items\\items.lst")
if lst_data:
    lines = lst_data.decode("latin-1").splitlines()
    for i, line in enumerate(lines):
        pid_num = i + 1
        # We want to find dynamite - check a few around common IDs
        # Actually let's just find it by reading protos and checking FID
        pass
    print(f"items.lst: {len(lines)} entries")

# Check the new pro files
for fname in new_pros:
    path = data_dir + fname
    with open(path, "rb") as f:
        data = f.read()
    parse_item_pro(data, fname)

# Also find and check a known dynamite proto from master.dat
# Dynamite FID in inventory: dynamit.frm is index 46 (0-based) in INVEN.LST
# FID = 0x00000000 | (46 << 16) ... actually let's just search
print("\nSearching master.dat for dynamite proto (FID with inven index 46 = 0x002E0000)...")
with open(dat_path, "rb") as f:
    f.seek(-8, 2)
    tree_size, data_size = struct.unpack("<II", f.read(8))
    total_size = f.seek(0, 2)
    tree_offset = total_size - tree_size - 8
    f.seek(tree_offset)
    num_files = struct.unpack("<I", f.read(4))[0]
    for _ in range(num_files):
        name_len = struct.unpack("<I", f.read(4))[0]
        name = f.read(name_len).decode("latin-1")
        comp, real_size, packed_size, offset = struct.unpack("<BIII", f.read(13))
        if "proto\\items\\" in name and name.endswith(".pro"):
            pos = f.tell()
            f.seek(offset)
            raw = f.read(packed_size)
            if comp == 1:
                raw = zlib.decompress(raw)
            if len(raw) >= 12:
                fid = struct.unpack(">I", raw[8:12])[0]
                if fid == 0x002E0000:
                    print(f"  Found: {name}, size={len(raw)}")
                    parse_item_pro(raw, name)
            f.seek(pos)
