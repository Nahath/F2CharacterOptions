"""
Read RP source RCDRJOHN.SSL, replace the RP-specific include block with
data/headers/ compatible includes, apply companion-implant targeting
changes, and write to data/scripts/rcdrjohn.ssl.
"""
from pathlib import Path

SRC = Path(r"C:\git\f2Mod\F2Modding\BIS mapper patched (+complementary ressources)\Updated source codes\RP 2.3.3 source codes by Killap\REDDING\RCDRJOHN.SSL")
DST = Path(r"C:\git\f2Mod\data\scripts\rcdrjohn.ssl")

NEW_HEADER = """\
#define SCRIPT_REALNAME "rcdrjohn"
#include "../headers/define.h"
#include "../headers/rcdrjohn.h"

#define NAME                    SCRIPT_RCDRJOHN
#define TOWN_REP_VAR            (GVAR_TOWN_REP_REDDING)

#include "../headers/command.h"
#include "../headers/modreact.h"
"""

NEW_PROCS = """
procedure NodeSelectTarget;
procedure NodeSlotPlayer;
procedure NodeSlotVic;
procedure NodeSlotSulik;
procedure NodeSlotMyron;
procedure NodeSlotMarcus;
procedure NodeSlotMacRae;
procedure NodeSlotLenny;
procedure NodeSlotCyberdog;
procedure NodeSlotDoc;
procedure NodeSlotGoris;
procedure NodeSlotDavin;
procedure NodeSlotMiria;
procedure NodeSlotDogmeat;
procedure NodeSlotK9;
procedure NodeSlotKitsune;
procedure NodeSlotDex;
procedure NodeSlotCatJules;
procedure NodeCheckTarget;
procedure NodeFullyImplanted;

"""

APPEND_PROCS = """
procedure NodeSelectTarget begin
   Reply(330);
   NOption(331, NodeSlotPlayer, 004);
   if (Vic_In_Party) then
      NOption(obj_name(Vic_Ptr), NodeSlotVic, 004);
   if (Sulik_In_Party) then
      NOption(obj_name(Sulik_Ptr), NodeSlotSulik, 004);
   if (Myron_In_Party) then
      NOption(obj_name(Myron_Ptr), NodeSlotMyron, 004);
   if (Marcus_In_Party) then
      NOption(obj_name(Marcus_Ptr), NodeSlotMarcus, 004);
   if (MacRae_In_Party) then
      NOption(obj_name(MacRae_Ptr), NodeSlotMacRae, 004);
   if (Lenny_In_Party) then
      NOption(obj_name(Lenny_Ptr), NodeSlotLenny, 004);
   if (Cyberdog_In_Party) then
      NOption(obj_name(Cyberdog_Ptr), NodeSlotCyberdog, 004);
   if (Doc_In_Party) then
      NOption(obj_name(Doc_Ptr), NodeSlotDoc, 004);
   if (Goris_In_Party) then
      NOption(obj_name(Goris_Ptr), NodeSlotGoris, 004);
   if (Davin_In_Party) then
      NOption(obj_name(Davin_Ptr), NodeSlotDavin, 004);
   if (Miria_In_Party) then
      NOption(obj_name(Miria_Ptr), NodeSlotMiria, 004);
   if (Dogmeat_In_Party) then
      NOption(obj_name(Dogmeat_Ptr), NodeSlotDogmeat, 004);
   if (K9_In_Party) then
      NOption(obj_name(K9_Ptr), NodeSlotK9, 004);
   if (Kitsune_In_Party) then
      NOption(obj_name(Kitsune_Ptr), NodeSlotKitsune, 004);
   if (Dex_In_Party) then
      NOption(obj_name(Dex_Ptr), NodeSlotDex, 004);
   if (Cat_Jules_In_Party) then
      NOption(obj_name(Cat_Jules_Ptr), NodeSlotCatJules, 004);
   NOption(332, Node017, 004);
end

procedure NodeSlotPlayer begin
   target_critter := dude_obj;
   call NodeCheckTarget;
end

procedure NodeSlotVic begin
   target_critter := Vic_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotSulik begin
   target_critter := Sulik_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotMyron begin
   target_critter := Myron_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotMarcus begin
   target_critter := Marcus_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotMacRae begin
   target_critter := MacRae_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotLenny begin
   target_critter := Lenny_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotCyberdog begin
   target_critter := Cyberdog_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotDoc begin
   target_critter := Doc_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotGoris begin
   target_critter := Goris_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotDavin begin
   target_critter := Davin_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotMiria begin
   target_critter := Miria_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotDogmeat begin
   target_critter := Dogmeat_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotK9 begin
   target_critter := K9_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotKitsune begin
   target_critter := Kitsune_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotDex begin
   target_critter := Dex_Ptr;
   call NodeCheckTarget;
end

procedure NodeSlotCatJules begin
   target_critter := Cat_Jules_Ptr;
   call NodeCheckTarget;
end

procedure NodeCheckTarget begin
   if ((has_trait(TRAIT_PERK,target_critter,PERK_dermal_enhancement_perk)) and (has_trait(TRAIT_PERK,target_critter,PERK_phoenix_enhancement_perk))) then
      call NodeFullyImplanted;
   else
      call Node049;
end

procedure NodeFullyImplanted begin
   Reply(333);
   NOption(332, NodeSelectTarget, 004);
end
"""

lines = SRC.read_text(encoding="latin-1").splitlines(keepends=True)

# Find the last #include line (ModReact) — everything before it is the old header block.
start = None
for i, line in enumerate(lines):
    if line.strip().startswith('#include') and 'ModReact' in line:
        start = i
        break

if start is None:
    raise RuntimeError("Could not find ModReact #include line")

body = "".join(lines[start + 1:])

# Insert target_critter variable declaration after the last From_5x var
body = body.replace(
    "variable From_53:=0;\n",
    "variable From_53:=0;\nvariable target_critter:=0;\n",
    1,
)

# Insert forward declarations for new procedures after the last existing forward decl
body = body.replace(
    "procedure Node053a;\n",
    "procedure Node053a;" + NEW_PROCS,
    1,
)

# Redirect implant entry point from Node049 to NodeSelectTarget
body = body.replace(
    "NOption(288,Node049,004);",
    "NOption(288,NodeSelectTarget,004);",
)

# Point all perk checks at target_critter instead of dude_obj
body = body.replace(
    "has_trait(TRAIT_PERK,dude_obj,",
    "has_trait(TRAIT_PERK,target_critter,",
)

# Point all implant grants/removals at target_critter
body = body.replace(
    "critter_add_trait(dude_obj,TRAIT_PERK,",
    "critter_add_trait(target_critter,TRAIT_PERK,",
)
body = body.replace(
    "critter_rm_trait(dude_obj,TRAIT_PERK,",
    "critter_rm_trait(target_critter,TRAIT_PERK,",
)

_add_stat = {
    "PERK_dermal_armor_perk": (
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist, get_critter_extra_stat(target_critter,STAT_dmg_resist) + 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_explosion, get_critter_extra_stat(target_critter,STAT_dmg_resist_explosion) + 5);"
        "\n   end"
    ),
    "PERK_dermal_enhancement_perk": (
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist, get_critter_extra_stat(target_critter,STAT_dmg_resist) + 10);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_explosion, get_critter_extra_stat(target_critter,STAT_dmg_resist_explosion) + 10);"
        "\n   end"
    ),
    "PERK_phoenix_armor_perk": (
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_laser, get_critter_extra_stat(target_critter,STAT_dmg_resist_laser) + 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_fire, get_critter_extra_stat(target_critter,STAT_dmg_resist_fire) + 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_plasma, get_critter_extra_stat(target_critter,STAT_dmg_resist_plasma) + 5);"
        "\n   end"
    ),
    "PERK_phoenix_enhancement_perk": (
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_laser, get_critter_extra_stat(target_critter,STAT_dmg_resist_laser) + 10);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_fire, get_critter_extra_stat(target_critter,STAT_dmg_resist_fire) + 10);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_plasma, get_critter_extra_stat(target_critter,STAT_dmg_resist_plasma) + 10);"
        "\n   end"
    ),
}

for _p in ("PERK_dermal_armor_perk", "PERK_dermal_enhancement_perk",
           "PERK_phoenix_armor_perk", "PERK_phoenix_enhancement_perk"):
    body = body.replace(
        "critter_add_trait(target_critter,TRAIT_PERK," + _p + ",1);",
        "critter_add_trait(target_critter,TRAIT_PERK," + _p + ",1);" + _add_stat[_p],
        1,
    )

for _p, _reversal in (
    ("PERK_dermal_armor_perk",
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist, get_critter_extra_stat(target_critter,STAT_dmg_resist) - 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_explosion, get_critter_extra_stat(target_critter,STAT_dmg_resist_explosion) - 5);"
        "\n   end"
    ),
    ("PERK_phoenix_armor_perk",
        "\n   if (target_critter != dude_obj) then begin"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_laser, get_critter_extra_stat(target_critter,STAT_dmg_resist_laser) - 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_fire, get_critter_extra_stat(target_critter,STAT_dmg_resist_fire) - 5);"
        "\n      set_critter_extra_stat(target_critter,STAT_dmg_resist_plasma, get_critter_extra_stat(target_critter,STAT_dmg_resist_plasma) - 5);"
        "\n   end"
    ),
):
    body = body.replace(
        "critter_rm_trait(target_critter,TRAIT_PERK," + _p + ",1);",
        "critter_rm_trait(target_critter,TRAIT_PERK," + _p + ",1);" + _reversal,
        1,
    )

result = NEW_HEADER + body + APPEND_PROCS

DST.write_text(result, encoding="latin-1")
print(f"Written {len(result)} chars to {DST}")
