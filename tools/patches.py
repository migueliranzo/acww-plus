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
]
