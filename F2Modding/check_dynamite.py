import struct, zlib

dat_path = "C:/Games/F2Modding/Fallout 2/master.dat"

# Extract items.lst from master.dat to find dynamite's proto number
def extract_file(dat_path, target_lower):
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
            if name.lower().replace("/", "\\") == target_lower:
                pos = f.tell()
                f.seek(offset)
                data = f.read(packed_size)
                if comp == 1:
                    data = zlib.decompress(data)
                return data
    return None

# Get items.lst from master.dat
lst_data = extract_file(dat_path, "proto\\items\\items.lst")
lines = lst_data.decode("latin-1").splitlines()

# Find dynamite entries by searching all item protos for ones with dynamit FID
# dynamit.frm index in INVEN.LST = 46 (0-based), FID = 0x0000002E
# dynon.frm = 115 (0-based), FID = 0x00000073
# Let's find them all

print("Searching for dynamite-related protos in master.dat...")
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
                if fid in (0x0000002E, 0x00000073):  # dynamit.frm or dynon.frm
                    pid = struct.unpack(">I", raw[0:4])[0]
                    item_num = pid & 0xFFFF
                    print(f"{name}: size={len(raw)}, PID={item_num}, FID=0x{fid:08X}")
                    print(f"  hex: {raw.hex()}")
            f.seek(pos)
