import struct, zlib

def extract_file(dat_path, target):
    try:
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
                if "scripts.lst" in name.lower() and "scripts" in name.lower():
                    pos = f.tell()
                    f.seek(offset)
                    raw = f.read(packed_size)
                    if comp == 1:
                        raw = zlib.decompress(raw)
                    return raw.decode("latin-1")
    except:
        pass
    return None

base = "C:/Games/F2Modding/Fallout 2/"
for dat in ["master.dat", "patch000.dat", "sfall.dat"]:
    data = extract_file(base + dat, "scripts.lst")
    if data:
        lines = data.splitlines()
        print(f"{dat}: {len(lines)} entries")
        print(f"  Last entry: {lines[-1].strip()}")
        # Save master.dat version
        if dat == "master.dat":
            with open("C:/Games/F2Modding/scripts_lst_base.txt", "w") as f:
                f.write(data)
            print(f"  Saved to scripts_lst_base.txt")
    else:
        print(f"{dat}: no scripts.lst found")
