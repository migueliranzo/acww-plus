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
]
