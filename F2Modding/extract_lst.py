import struct, zlib

dat_path = "C:/Games/F2Modding/Fallout 2/master.dat"
targets = ["art\\inven\\INVEN.LST", "art\\inven\\NEW.LST"]

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
        if name in targets:
            pos = f.tell()
            f.seek(offset)
            data = f.read(packed_size)
            if comp == 1:
                data = zlib.decompress(data)
            print("=== " + name + " ===")
            print(data.decode("latin-1"))
            f.seek(pos)
