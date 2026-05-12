"""Find Sajag's proto by scanning master.dat critter protos for Klamath candidates."""
import struct, zlib
from pathlib import Path

CANDIDATES = {52, 53, 54, 57, 58, 59, 60, 55, 56}

def read_dat_all_prefix(dat_path, prefix):
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
        norm = name.replace("/", "\\").lower()
        if norm.startswith(prefix.lower()):
            with open(dat_path, "rb") as fh:
                fh.seek(offset)
                raw = fh.read(packed)
            data = zlib.decompress(raw) if comp else raw
            results[norm] = data
    return results

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
print("Scanning master.dat for critter protos...")
protos = read_dat_all_prefix(game / "master.dat", "proto\\critters\\")
print(f"Found {len(protos)} critter protos")

for path, data in sorted(protos.items()):
    fname = path.split("\\")[-1]
    try:
        pid_num = int(fname.replace(".pro", ""))
    except ValueError:
        continue
    if pid_num not in CANDIDATES:
        continue
    if len(data) < 32:
        continue
    stored_pid = struct.unpack_from(">I", data, 0)[0]
    text_id    = struct.unpack_from(">I", data, 4)[0]
    frm_id     = struct.unpack_from(">I", data, 8)[0]
    sid_24     = struct.unpack_from(">i", data, 24)[0]
    sid_28     = struct.unpack_from(">i", data, 28)[0] if len(data) > 31 else -1
    print(f"proto {pid_num:3d}: text_id={text_id} name_msg={text_id*100} frm={frm_id:#010x} sid@24={sid_24} sid@28={sid_28}")
