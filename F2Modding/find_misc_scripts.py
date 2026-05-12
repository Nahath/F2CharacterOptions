import struct, zlib

# Find proto script IDs for flare, stealth boy, motion sensor - items with active versions
# Also extract and decompile any related INT scripts from the DATs

ITEM_PIDS = {
    # pid: name
    69: "Flare",
    205: "Active Flare",
    54: "Stealth Boy",
    210: "Active Stealth Boy",
    59: "Motion Sensor",
    208: "Active Motion Sensor",
    51: "Dynamite",
    206: "Active Dynamite",
}

def read_dat(dat_path):
    results = {}
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
                results[name.lower()] = (comp, packed_size, offset, f)
    except:
        pass
    return results

def extract(dat_path, path_lower):
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
                if name.lower().replace("/","\\") == path_lower:
                    f.seek(offset)
                    raw = f.read(packed_size)
                    if comp == 1:
                        raw = zlib.decompress(raw)
                    return raw
    except:
        pass
    return None

base = "C:/Games/F2Modding/Fallout 2/"
dats = ["master.dat", "patch000.dat"]

print("=== Proto script IDs for misc items with active versions ===")
for dat in dats:
    for pid, name in ITEM_PIDS.items():
        pro_path = f"proto\\items\\{pid:08d}.pro"
        data = extract(base + dat, pro_path)
        if data and len(data) >= 32:
            script_id = struct.unpack(">i", data[28:32])[0]
            if script_id != -1:
                print(f"  {dat}: PID {pid} ({name}): script_id={script_id}")

print()
print("=== Scripts LST - looking for flare/stealthboy/motion entries ===")
for dat in dats:
    lst = extract(base + dat, "scripts\\scripts.lst")
    if lst:
        lines = lst.decode("latin-1").splitlines()
        for i, line in enumerate(lines):
            l = line.lower()
            if any(x in l for x in ["flar","stealth","motion","misc","item","genitem"]):
                print(f"  line {i+1}: {line.strip()}")
        break
