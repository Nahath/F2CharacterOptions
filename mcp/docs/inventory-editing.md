# Editing NPC and Container Inventory in Fallout 2

---

## Two mechanisms

Every item in a container or NPC's barter stock reaches the player through one
or both of these mechanisms:

| Mechanism | What it controls | How to edit |
|-----------|-----------------|-------------|
| **MAP static inventory** | Items present on day-1 of a fresh game | Patch the `.map` file in Python (`install.py`) |
| **Restock script** | Items replenished after being sold/taken | Edit the `.ssl` source, compile, bundle `.int` |

**Restock takes priority over static inventory.**  If an item is in the MAP
but not in the restock script, it disappears after being bought and never
returns.  The canonical approach is: use MAP static inventory for day-1
presence of an item, and include the same item in the restock script so it
returns after being sold.

---

## Restock scripts

### Finding the right script

An NPC's restock script is typically a container object (a "stock box") whose
script runs `check_restock_item(pid, min, max, chance)` on map enter.  The
NPC's talk script then calls `move_obj_inven_to_obj(box_obj, self_obj)` to
transfer all box items to the NPC for barter.

To find the script for a given NPC:
1. Open their talk script source (e.g. `kcsajag.ssl`), look for
   `move_obj_inven_to_obj` — the first argument is the box object.
2. The box object's script is registered in `scripts.lst`; its source is
   in the RPU GitHub under `scripts_src/<area>/`.

### The check_restock_item macro

```ssl
check_restock_item(PID_CONSTANT, min_qty, max_qty, chance_pct)
```

- **PID_CONSTANT** — SSL define from `data/headers/itempid.h`.  These are
  **internal PIDs** (offset 0 of the `.pro` file), not file numbers.  Use
  `inspect_proto` to confirm.  See `proto-format.md` for items where the two
  differ.
- **min_qty / max_qty** — a random target quantity is chosen each cycle.
- **chance_pct** — 1–100; 100 = always restock.

### Editing the restock list

1. Open the script's `.ssl` source in `data/scripts/`.
2. Add, remove, or edit `check_restock_item(...)` calls in `map_enter_p_proc`.
3. Compile:  `compile_ssl("data\scripts\<name>.ssl")`
4. The installer reads the compiled `.int` from `data/scripts/` and bundles it.
   No changes to `install.py` are needed for restock-only edits.

### Header dependencies

Restock scripts compiled from RPU source require a full header chain.
All needed headers are already present in this project:

- `data/headers/` — RPU headers (define.h, command.h, itempid.h, scripts.h, etc.)
- `data/sfall/` — sfall headers (sfall.h, lib.math.h)

Do not delete these.  Compiling any RPU-sourced `.ssl` depends on them.

---

## MAP static inventory

Items are placed directly in a container object's inventory in the `.map` file.
They appear on day-1 without waiting for a restock cycle.

**Rules:**

- The proto's `ScriptID` must be `-1`.  A scripted proto in a container's
  static MAP inventory causes a black screen on fresh map load.
- Weapon items (subtype 3) require correct ammo-state in their 8 extra bytes.
  No-ammo weapons (melee, thrown): `ammo_type=0, ammo_count=0xFFFFFFFF`.
  Setting `ammo_count=0` causes a crash on container open.
  See `debugging-facts.md` §"Weapon-type items in container static inventory".
- Safe subtypes: Armor (0 extra bytes), Drug (4 bytes, 0 valid),
  Misc (4 bytes, 0 valid), Ammo (4 bytes, 0 valid).
- Use the **file number** in `proto_pid`, not the internal PID.  See
  `proto-format.md` for the distinction and a table of known mismatches.

The MAP patch is implemented in `install.py`; see the patching recipe in
`map-format.md` for the byte layout.

---

---

## Stealable-but-not-barterable NPC items

To give an NPC a personal item that can be stolen but never appears in their
barter screen, use the **temp-container pattern** in the NPC's talk script:

```ssl
variable temp_box;

procedure talk_p_proc begin
    // Park personal items before barter
    temp_box := create_object(63, 0, 0);     // proto 63 = generic Container
    move_obj_inven_to_obj(self_obj, temp_box);

    // Load barter items from the barter box into self
    move_obj_inven_to_obj(klam_sajag_box_obj, self_obj);

    // ... dialogue and barter_with(self_obj) ...

    // Return barter items to box, restore personal items
    move_obj_inven_to_obj(self_obj, klam_sajag_box_obj);
    move_obj_inven_to_obj(temp_box, self_obj);
    destroy_object(temp_box);
end
```

The personal items are never in `self_obj` at the moment barter runs, so they
don't appear in the barter screen.  They are restored immediately after.

To give the NPC the item in the first place, use `map_enter_p_proc` with a
local-var guard so it only runs once:

```ssl
#define LVAR_Item_Given (12)   // next free slot after the NPC's existing LVARs

if (local_var(LVAR_Item_Given) == 0) then begin
    set_local_var(LVAR_Item_Given, 1);
    variable item;
    item := create_object(PID_ITEM, 0, 0);
    add_obj_to_inven(self_obj, item);
end
```

**Worked example:** Sajag (kcsajag.ssl) — Advanced Power Armor (PID 348) placed in
`map_enter_p_proc` with `LVAR_APA_Given` (slot 12) guard; temp-container pattern
in `talk_p_proc` keeps it off the barter screen.

This mirrors the Smitty (The Den) design in vanilla/RPU.

---

## Worked example: Sajag (Klamath)

Sajag's barter inventory is managed by the Kisbox container (proto 63,
tile 15121 in `kladwtwn.map`).  Its restock script source is at
`data/scripts/kisbox.ssl`.

**Current restock list:**

| SSL constant | Internal PID | Item | qty range | chance |
|---|---|---|---|---|
| `PID_BOTTLE_CAPS` | 41 | Money (caps) | 125–250 | 100% |
| `PID_POWERED_ARMOR` | 3 | Power Armor T-51b | 1–1 | 100% |
| `PID_KNIFE` | 4 | Knife | 1–2 | 100% |
| `PID_THROWING_KNIFE` | 45 | Throwing Knife | 2–4 | 100% |
| `PID_10MM_JHP` | 29 | 10mm JHP | 0–3 | 100% |
| `PID_STIMPAK` | 40 | Stimpak | 2–4 | 100% |
| `PID_SUPER_STIMPAK` | 144 | Super Stimpak | 1–2 | 100% |
| `PID_MEAT_JERKY` | 284 | Meat Jerky | 3–4 | 100% |
| `PID_BEER` | 124 | Beer | 3–6 | 100% |
| `PID_BOOZE` | 125 | Booze | 2–4 | 100% |
| `PID_LEATHER_ARMOR` | 1 | Leather Armor | 0–1 | 50% |
| `PID_10MM_PISTOL` | 8 | 10mm Pistol | 0–1 | 100% |
| `PID_SPEAR` | 7 | Spear | 1–2 | 100% |
| `PID_M72_GAUSS_RIFLE` | 392 | M72 Gauss Rifle | 0–2 | 100% |
| `PID_RADAWAY` | 48 | RadAway | 0–2 | 100% |

Power Armor is also placed as a MAP static item (file number 14, ScriptID=-1)
so it is present on day-1 of a fresh game.

