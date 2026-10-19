"""
Declarative patch table for AC:WW+ (EU ADMP). Read by tools/build_rom.py.

Each patch: (module, address, kind, expected_hex, value, note)
  module  : "arm9" (main, loads at 0x02000000) or "ovNNN"
  kind    : "bl"    -> Thumb BL at address to payload symbol `value`
            "bytes" -> raw bytes `value` (hex string)
            "ptr"   -> u32 pointer to payload symbol `value` (Thumb bit set)
  expected: vanilla bytes at address (hex), checked before patching
"""

PATCHES = [
    # --- Feature 1: furniture outdoors (src/outdoor_furniture.c) ---
    ("ov003", 0x022212C2, "bl", "90300068", "hook_ov003_draw_item", "item draw loop, cat 1/3/4 branch"),
    ("ov003", 0x022212C6, "bytes", "2af6", "18e0", "b 0x022212FA (skip the vanilla icon path)"),
    ("ov003", 0x02220ADA, "bl", "24f6fbfc", "hook_ov003_teardown", "outdoor scene teardown"),
    ("arm9", 0x020B2A90, "bl", "70f162fd", "hook_ov003_item_shape", "town_query_item_shape -> ov003_item_shape"),
    ("arm9", 0x02042DB4, "bl", "00f006f8", "hook_outdoor_drop_item", "outdoor drop -> func_02042dc4"),
    ("arm9", 0x02042B7A, "bl", "00f04bf8", "hook_field_put_spot_check", "field_put_spot_find -> spot check"),

    # --- Feature 8: Nookington's without a visitor purchase ---
    # shop_visitor_sale_flag_test (only caller: shop_next_stage) -> movs r0,#1; bx lr
    ("arm9", 0x020AEA8C, "bytes", "01480721", "01207047", "Nookington's: visitor-purchase flag always set"),

    # --- Feature 7: monkeys obtainable ---
    # Species table 0x020CC9B8 (150 x 0x4E), +0x4B move class: 0 starter or move-in, 1 move-in only, 2 never.
    # Champ, Nana, Simon, Tammi, Monty, Elise (0x90-0x95) are class 2 in vanilla -> class 0.
    ("arm9", 0x020CF5E3, "bytes", "02", "00", "Champ (species 0x90) class 2 -> 0"),
    ("arm9", 0x020CF631, "bytes", "02", "00", "Nana (species 0x91) class 2 -> 0"),
    ("arm9", 0x020CF67F, "bytes", "02", "00", "Simon (species 0x92) class 2 -> 0"),
    ("arm9", 0x020CF6CD, "bytes", "02", "00", "Tammi (species 0x93) class 2 -> 0"),
    ("arm9", 0x020CF71B, "bytes", "02", "00", "Monty (species 0x94) class 2 -> 0"),
    ("arm9", 0x020CF769, "bytes", "02", "00", "Elise (species 0x95) class 2 -> 0"),

    # --- Feature 6: tools swapped / put away with L/R (src/tool_swap.c) ---
    # Action 2 (stand) tick: rodata pair {fn, 0} copied into the action tick table by func_02005368.
    ("arm9", 0x020D65A4, "ptr", "69cc0002", "hook_player_stand_tick", "stand tick -> tool swap poll"),
    ("arm9", 0x020D6804, "ptr", "d9c30002", "hook_player_action05_tick", "action 5 (item-selected pose) tick -> back to stand after an L/R equip"),
    ("arm9", 0x020D6634, "ptr", "39950002", "hook_player_action3f_tick", "action 0x3F (equip) tick -> buffer L/R taps"),
    ("arm9", 0x020D680C, "ptr", "71c40002", "hook_player_skid_tick", "action 4 (skid) tick -> buffer L/R taps"),
    ("arm9", 0x020D6814, "ptr", "c9c60002", "hook_player_walk_tick", "action 3 (walk) tick -> buffer L/R taps"),

    # --- Feature 5: shake trees with a rod or net equipped (src/tree_shake.c) ---
    # func_ov003_022085dc (A-button use handler) -> func_ov003_02208430 (dispatch by tool kind), 8 calls
    ("ov003", 0x022085FE, "bl", "fff717ff", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x02208696, "bl", "fff7cbfe", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x022086B8, "bl", "fff7bafe", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x022086D6, "bl", "fff7abfe", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x022087FC, "bl", "fff718fe", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x022088A8, "bl", "fff7c2fd", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x02208916, "bl", "fff78bfd", "hook_ov003_use_dispatch", "use handler -> dispatch"),
    ("ov003", 0x02208946, "bl", "fff773fd", "hook_ov003_use_dispatch", "use handler -> dispatch"),
]
