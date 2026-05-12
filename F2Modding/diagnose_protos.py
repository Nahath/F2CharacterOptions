import struct, zlib

data_dir = "C:/Games/F2Modding/Fallout 2/data/"

# Read INVEN.LST so we can resolve FIDs
with open(data_dir + "art/inven/INVEN.LST", "r") as f:
    inven_lst = [line.strip() for line in f if line.strip()]

print(f"INVEN.LST has {len(inven_lst)} entries")

def parse_proto(path, label):
    with open(path, "rb") as f:
        data = f.read()
    pid        = struct.unpack(">I", data[0:4])[0]
    msg_id     = struct.unpack(">I", data[4:8])[0]
    fid        = struct.unpack(">I", data[8:12])[0]
    flags      = struct.unpack(">I", data[20:24])[0]
    script_id  = struct.unpack(">i", data[28:32])[0]
    item_type  = struct.unpack(">I", data[32:36])[0]
    inv_fid    = struct.unpack(">I", data[52:56])[0] if len(data) >= 56 else -1

    inv_art_type = (inv_fid >> 24) & 0xFF
    inv_idx      = inv_fid & 0x00FFFFFF

    inv_name = inven_lst[inv_idx] if inv_idx < len(inven_lst) else f"OUT OF RANGE (max {len(inven_lst)-1})"

    # Check Use action flag (bit 5 of flags2 or specific flag value)
    # Vanilla dynamite flags at offset 20: 0xA0000008
    use_flag = "YES" if (flags & 0xA0000008) else "NO"

    print(f"\n=== {label} ===")
    print(f"  PID:         {pid}")
    print(f"  script_id:   {script_id}  {'<-- STILL ASSIGNED, will conflict!' if script_id != -1 else '(none, good)'}")
    print(f"  item_type:   {item_type}  {'(misc, correct)' if item_type == 5 else '(WRONG, must be 5)'}")
    print(f"  flags @20:   0x{flags:08X}  {'(matches vanilla dynamite)' if flags == 0xA0000008 else '(DIFFERS from vanilla 0xA0000008)'}")
    print(f"  ground FID:  0x{fid:08X}")
    print(f"  inv FID:     0x{inv_fid:08X}  (art_type={inv_art_type}, index={inv_idx})")
    print(f"  inv FRM:     {inv_name}")

parse_proto(data_dir + "proto/items/00000534.pro", "PID 534 - Super Dynamite")
parse_proto(data_dir + "proto/items/00000535.pro", "PID 535 - Active Super Dynamite")

# Also show what vanilla dynamite has for comparison
import os
def extract_from_dat(dat_path, target):
    with open(dat_path, "rb") as f:
        f.seek(-8, 2)
        tree_size, _ = struct.unpack("<II", f.read(8))
        total = f.seek(0, 2)
        f.seek(total - tree_size - 8)
        n = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            nlen = struct.unpack("<I", f.read(4))[0]
            name = f.read(nlen).decode("latin-1")
            comp, real_size, packed, offset = struct.unpack("<BIII", f.read(13))
            if name.lower().replace("/","\\") == target.lower():
                pos = f.tell(); f.seek(offset)
                raw = f.read(packed)
                if comp == 1: raw = zlib.decompress(raw)
                f.seek(pos); return raw
    return None

vanilla = extract_from_dat("C:/Games/F2Modding/Fallout 2/master.dat",
                           "proto\\items\\00000051.pro")
if vanilla:
    v_inv_fid = struct.unpack(">I", vanilla[52:56])[0]
    v_inv_idx = v_inv_fid & 0x00FFFFFF
    v_flags   = struct.unpack(">I", vanilla[20:24])[0]
    v_name    = inven_lst[v_inv_idx] if v_inv_idx < len(inven_lst) else "out of range"
    print(f"\n=== Vanilla Dynamite (PID 51) for reference ===")
    print(f"  flags @20:  0x{v_flags:08X}")
    print(f"  inv FID:    0x{v_inv_fid:08X}  (index={v_inv_idx})")
    print(f"  inv FRM:    {v_name}")
