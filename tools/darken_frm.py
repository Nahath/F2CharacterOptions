"""
darken_frm.py
─────────────
Creates a darkened copy of an FRM sprite file for Dynamite MKII by reading
each pixel's palette index, looking up its RGB colour in the game's colour
palette, reducing the brightness, finding the nearest available palette
colour, and writing the result as a new FRM.

Usage:
    python tools/darken_frm.py <game_data_dir> [--factor FACTOR]

    <game_data_dir>  Path to your Fallout 2 "data" directory.
    --factor FACTOR  Brightness multiplier in (0.0, 1.0].  Default: 0.65
                     0.65 produces a noticeably darker but still
                     recognisable icon.

The script reads:
    art/items/DYNAMIT.FRM     (vanilla dynamite inventory sprite)
    color.pal                 (Fallout 2 256-colour palette, 768 bytes)

And writes:
    art/items/DYNMK2.FRM      (Dynamite MKII inventory sprite)

After running this script, update 600.pro's FID to point at DYNMK2.FRM.
See README.md § "Updating the FID in 600.pro" for instructions.

FRM file format reference:
    https://fallout.wiki/wiki/FRM_File_Format

PAL file format:
    768 bytes — 256 entries × 3 bytes (R, G, B), values 0–63 (6-bit).
    Multiply by 4 to convert to 0–255 range.
"""

import struct
import sys
import os
import argparse
import math

# ── FRM source / destination filenames ───────────────────────────────────────

SRC_FRM_NAME = "DYNAMIT.FRM"   # vanilla dynamite sprite
DST_FRM_NAME = "DYNMK2.FRM"    # Dynamite MKII sprite

DEFAULT_DARKEN_FACTOR = 0.65   # reduce brightness to 65 %

# ── PAL helpers ──────────────────────────────────────────────────────────────

def load_palette(pal_path: str):
    """
    Return a list of 256 (r, g, b) tuples in 0-255 range.
    Fallout 2 stores palette components as 6-bit values (0-63).
    """
    with open(pal_path, "rb") as f:
        raw = f.read(768)
    if len(raw) < 768:
        raise ValueError(f"Palette file too short: {len(raw)} bytes (expected 768).")
    palette = []
    for i in range(256):
        r = raw[i * 3]     * 4
        g = raw[i * 3 + 1] * 4
        b = raw[i * 3 + 2] * 4
        palette.append((r, g, b))
    return palette


def nearest_palette_index(palette, r: int, g: int, b: int) -> int:
    """Return the palette index whose colour is closest to (r, g, b)."""
    best_idx  = 0
    best_dist = float("inf")
    for idx, (pr, pg, pb) in enumerate(palette):
        dist = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dist < best_dist:
            best_dist = dist
            best_idx  = idx
            if dist == 0:
                break
    return best_idx


def darken_index(palette, idx: int, factor: float) -> int:
    """Return the palette index closest to the given index's colour darkened by factor."""
    r, g, b = palette[idx]
    dr = int(r * factor)
    dg = int(g * factor)
    db = int(b * factor)
    return nearest_palette_index(palette, dr, dg, db)


def build_remap_table(palette, factor: float) -> bytes:
    """Build a 256-byte lookup table: old_index → darkened_index."""
    return bytes(darken_index(palette, i, factor) for i in range(256))

# ── FRM helpers ──────────────────────────────────────────────────────────────

def parse_frm_header(data: bytes):
    """
    Parse the 62-byte FRM header and return a dict of fields plus the
    offset at which frame data begins.

    FRM header layout (all big-endian):
      0  uint32  version
      4  uint16  fps
      6  uint16  action_frame
      8  uint16  frames_per_direction
     10  int16[6] pixel_shift_x  (12 bytes)
     22  int16[6] pixel_shift_y  (12 bytes)
     34  uint32[6] frame_data_offset  (24 bytes) — offset from END of header
     58  uint32  total data size (bytes after the header)
    Total: 62 bytes
    """
    if len(data) < 62:
        raise ValueError("FRM file too short to contain a valid header.")
    version          = struct.unpack_from(">I", data,  0)[0]
    fps              = struct.unpack_from(">H", data,  4)[0]
    action_frame     = struct.unpack_from(">H", data,  6)[0]
    frames_per_dir   = struct.unpack_from(">H", data,  8)[0]
    pixel_shift_x    = struct.unpack_from(">6h", data, 10)
    pixel_shift_y    = struct.unpack_from(">6h", data, 22)
    frame_data_offset= struct.unpack_from(">6I", data, 34)
    data_size        = struct.unpack_from(">I", data,  58)[0]
    return dict(
        version=version,
        fps=fps,
        action_frame=action_frame,
        frames_per_dir=frames_per_dir,
        pixel_shift_x=list(pixel_shift_x),
        pixel_shift_y=list(pixel_shift_y),
        frame_data_offset=list(frame_data_offset),
        data_size=data_size,
        header_size=62,
    )


def remap_pixels(frame_data: bytearray, remap: bytes) -> None:
    """Remap all pixel bytes in-place using the provided 256-byte lookup."""
    for i in range(len(frame_data)):
        frame_data[i] = remap[frame_data[i]]

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a darkened FRM icon for Dynamite MKII.")
    parser.add_argument("game_data_dir",
                        help="Path to Fallout 2 data/ directory.")
    parser.add_argument("--factor", type=float, default=DEFAULT_DARKEN_FACTOR,
                        help=f"Brightness factor (default: {DEFAULT_DARKEN_FACTOR}).")
    args = parser.parse_args()

    if not (0.0 < args.factor <= 1.0):
        print("ERROR: --factor must be in (0.0, 1.0].")
        sys.exit(1)

    game_data_dir = args.game_data_dir
    pal_path      = os.path.join(game_data_dir, "color.pal")
    src_frm_path  = os.path.join(game_data_dir, "art", "items", SRC_FRM_NAME)
    dst_frm_path  = os.path.join(game_data_dir, "art", "items", DST_FRM_NAME)

    for path in (pal_path, src_frm_path):
        if not os.path.isfile(path):
            print(f"ERROR: File not found: {path}")
            sys.exit(1)

    print(f"Loading palette : {pal_path}")
    palette = load_palette(pal_path)

    print(f"Building remap  : factor={args.factor}")
    remap = build_remap_table(palette, args.factor)

    print(f"Reading source  : {src_frm_path}")
    with open(src_frm_path, "rb") as f:
        src_data = f.read()

    header = parse_frm_header(src_data)
    frame_data = bytearray(src_data[header["header_size"]:])

    print(f"Remapping pixels ({len(frame_data)} bytes) …")
    remap_pixels(frame_data, remap)

    out_data = src_data[:header["header_size"]] + bytes(frame_data)

    print(f"Writing output  : {dst_frm_path}")
    with open(dst_frm_path, "wb") as f:
        f.write(out_data)

    print()
    print("Done.")
    print()
    print("Next step: update the FID in 600.pro to point at DYNMK2.FRM.")
    print("See README.md § 'Updating the FID in 600.pro'.")


if __name__ == "__main__":
    main()
