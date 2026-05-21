# Current Session

## Task
Added Mass Lobber perk (requires ST 5 + Level 9, reduces throw AP cost by 2). Both Mass Lobber and Fast Reload are working.

## Progress
- gl_fastreload.ssl: registers both Fast Reload and Mass Lobber as fake selectable perks via sfall
- hs_calcapcost.ssl: HOOK_CALCAPCOST hook applies AP reductions for both perks
- mcp/docs/debugging-facts.md: updated with Fake Selectable Perks and HOOK_CALCAPCOST facts
- All scripts compiled and installed via install.py
- Committed.

## Next Step
None — session complete. Next work involves additional perks.

## Open Questions / Decisions
None.

## Context
Key bugs fixed this session:
1. perk_add_mode must be a direct opcode call, not sfall_func1 metarule
2. ADD_PERK_MODE_REMOVE (flag 4) causes crash on perk selection — use ADD_PERK_MODE_PERK (2) only
3. HOOK_CALCAPCOST arg4 (weapon) can be garbage (e.g. 5) — always use critter_inven_obj instead
4. PROTO_FLAG_EXT (offset 24) stores packed attack modes; lower nibble = primary, upper = secondary
5. Hook fires multiple times per action — read vanilla AP cost from proto, not hook arg, to avoid compounding
