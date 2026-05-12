"""List critter proto IDs present in critter.dat that also appear in kladwtwn.map."""
import struct, zlib
from pathlib import Path

CANDIDATES = {52, 53, 54, 57, 58, 59, 60}  # proto IDs near 56 on kladwtwn.map

def list_and_read_dat(dat_path):
    results = {}
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1"); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        if "proto" in name.lower() and "critter" in name.lower() and name.lower().endswith(".pro"):
            try:
                pid_str = name.split("\\")[-1].split("/")[-1].replace(".pro", "").replace(".PRO", "")
                pid_num = int(pid_str)
            except ValueError:
                continue
            if pid_num in CANDIDATES or True:  # get all
                with open(dat_path, "rb") as fh:
                    fh.seek(offset)
                    raw = fh.read(packed)
                data = zlib.decompress(raw) if comp else raw
                results[pid_num] = data
    return results

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
protos = list_and_read_dat(game / "critter.dat")
print(f"Found {len(protos)} critter protos")

# For each candidate, show proto fields
# Critter proto layout (big-endian):
#   0  PID           uint32
#   4  TextID        uint32   (text ID * 100 for name, +1 for desc)
#   8  FrmID         uint32   (animation set)
#  12  LightDist     uint16
#  14  LightIntens   uint16
#  16  Flags         uint32
#  20  ExtFlags      uint32
#  24  SID           int32    (ScriptID — usually -1 for critters)
#  28  ???
# Note: layout may vary — let's dump FrmID and TextID for identification

for pid in sorted(CANDIDATES):
    if pid not in protos:
        print(f"proto {pid}: NOT FOUND in critter.dat")
        continue
    data = protos[pid]
    if len(data) < 32:
        print(f"proto {pid}: too short ({len(data)} bytes)")
        continue
    stored_pid = struct.unpack_from(">I", data, 0)[0]
    text_id    = struct.unpack_from(">I", data, 4)[0]
    frm_id     = struct.unpack_from(">I", data, 8)[0]
    sid        = struct.unpack_from(">i", data, 24)[0]
    print(f"proto {pid:3d}: stored_pid={stored_pid} text_id={text_id} (name_id={text_id*100 if text_id else '?'}) frm_id={frm_id:#010x} sid_at24={sid}")
