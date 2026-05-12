# f2Mod — Fallout 2 Mod

Implements four changes to Fallout 2.  Requires **Sfall 4.3.4 or newer**
(the community DLL extender, `ddraw.dll`).

---

## Changes

| # | Description |
|---|-------------|
| 1 | Power armor can raise Strength above 10 (nothing else will). |
| 2 | Steal skill > 60 allows stealing equipped weapons. |
| 3 | Dynamite MKII — double damage and value, sold by Sajag at The Golden Gecko in Klamath. |
| 4 | Goris can wear the Bridgekeeper's Robes but no other armor. |

---

## Requirements

- Fallout 2 (any version; Restoration Project recommended but not required)
- [Sfall](https://github.com/sfall-team/sfall) 4.3.4 or newer
- Python 3.8+

---

## Installation

```
python install.py "C:\Games\Fallout2"
```

Pass the path to your Fallout 2 folder (the one that contains `fallout2.exe`).
The script will prompt for it if you don't include it on the command line.

The installer:
1. Copies the compiled script files (`.int`) to `data/scripts/`
2. Creates the Dynamite MKII item proto (`600.pro`) in `data/proto/items/`
3. Appends the Dynamite MKII name and description to `data/text/english/game/pro_item.msg`
4. Registers the global scripts in `sfall.cfg` (or `ddraw.ini`)

---

## Optional: darkened Dynamite MKII icon

By default Dynamite MKII uses the same inventory icon as regular dynamite.
To give it a slightly darker icon, run:

```
python tools/darken_frm.py "C:\Games\Fallout2\data"
```

This creates `data/art/items/DYNMK2.FRM`.  Then open `data/proto/items/00000600.pro`
in a hex editor and update the FID field at offset `0x0008` to reference `DYNMK2.FRM`.

---

## Compatibility

### Sfall version requirements

| Feature used | Minimum Sfall |
|--------------|---------------|
| `sfall_func2("set_stat_max", ...)` | 4.x |
| `HOOK_INVENTORYMOVE` | 4.x |
| `HOOK_STEAL` | 4.x |
| `set_proto_data` | 4.x |
| `party_member_list_critters`, `len_array`, `get_array` | 4.x |
| `unwield_slot` | 4.x |
| `objects_in_radius` | 4.x |
| `set_global_script_repeat` | 4.x |

### Steal interface and equipped items

Change 2 only fires when the steal interface presents an equipped item to the
player.  Sfall 4.2+ exposes equipped items in the pickpocket interface;
earlier versions do not, in which case the hook never fires for equipped weapons.

### Restoration Project

All proto IDs use vanilla Fallout 2 values.  The Restoration Project may change
or reassign some of these.  If items appear with wrong names or behaviours,
verify the PIDs against your installation's `proto/` directory and update the
`#define` constants in the relevant `.ssl` files.

---

## File reference

```
f2Mod/
├── install.py                         Installer — run this
├── data/
│   ├── scripts/
│   │   ├── hs_inventorymove.ssl/int   Hook: PA strength cap (Change 1)
│   │   ├── gl_powerarmor.ssl/int      Global: PA cap on load (Change 1)
│   │   ├── hs_steal.ssl/int           Hook: steal equipped weapons (Change 2)
│   │   ├── dynamitemk2.ssl/int        Item script: Dynamite MKII (Change 3)
│   │   ├── gl_klamath.ssl/int         Global: stock Sajag's inventory (Change 3)
│   │   └── gl_goris_armor.ssl/int     Global: Goris armor enforcement (Change 4)
│   └── text/english/game/
│       └── pro_item.msg               Additions only (installer appends these)
└── tools/
    ├── create_dynamitemk2_proto.py    Called by installer; also usable standalone
    └── darken_frm.py                  Optional: creates darker DYNMK2.FRM icon
```

---

## Recompiling from source

The `.int` files are pre-built.  To recompile after modifying a `.ssl` file,
use the Sfall edition of `compile.exe` from
[sfall-team/sslc](https://github.com/sfall-team/sslc/releases) with the `-p`
flag (required for preprocessor support):

```
compile.exe -q -l -p data\scripts\<name>.ssl
```

`DEFINE.H`, `SFALL.H`, and `define_extra.h` must be in the same directory as
the `.ssl` file (they are already present in `data/scripts/`).
