# Japanese version (Oide yo Doubutsu no Mori, ADMJ): port findings

Dump: `0193 Oide yo Doubutsu no Mori (JP).nds`, game code `ADMJ`, rev 0, 33,554,432 bytes, CRC32 `76E797D8`,
SHA-1 `343335ca958158b0e55d594832a1eeb977a953cf`. Region `jp` in `tools/regions/__init__.py`, vanilla files in
`vanilla/ADMJ/extracted` of the main checkout.

## What maps automatically
- `tools/remap_region.py jp` finds all 160 addresses and 54 patch sites (`tools/regions/admj.py`).
- Overlays are numbered like US rev 0 (EU ov018 and ov056 missing; the pattern editor ov123 is JP ov121).
- Build constants: code home `0x02296CE0`, arena-lo literal `0x02113D94`, autoload 2 at `0x020E7360`.
- Save magic (byte 0 of a save block): `0x32` (EU `0xC5`, US `0x8A`), check at JP `0x0209DE9C`.
- `ftr/` has the same file list as the EU.

## What does not: the data layouts differ
JP names are shorter (town names 2 bytes shorter, so each `VillagerIdent` is 0xA bytes instead of 0xC), and
the letter, player and save structures shrink with them. Found by pairing literal-pool constants of ~2,500 matched
functions (EU -> JP), then checked against the code:

| What | EU | JP | Evidence |
|---|---|---|---|
| Save block size / main checksum | 0x15FE0 / +0x15FDC | 0x12224 / +0x12220 | 7 / 2 functions |
| Town flag word | +0x15FD8 | +0x1221C | town_flag_set/clear/test |
| Store record | +0x15DB4 | +0x12008 | 3 functions |
| Nested checksum ranges | 0x10C3C (+0x84C), 0x15C58 (+0xF8) | 0xEBF8 (+0x694), 0x11F14 (+?) | save_image_fill, save_verify_slot |
| Player record size | 0x228C | 0x1D10 | 13 functions |
| Player pocket struct | +0x1148 | +0x1108 | player_record_ctor |
| Pocket items / flags / wallet (in the pocket struct) | +0x9DA / +0x9FC / +0x9F8 | +0x59E / +0x5C0 / +0x5BC | pocket_write_slot, pocket_slot_flags, wallet_get |
| -> player-relative pockets / flags | 0x1B22 / 0x1B44 | 0x16A6 / 0x16C8 | |
| Held item | 0x220A | 0x1C96 | player_record_ctor |
| Hair type / hair colour + tan | 0x223C / 0x223D | 0x1CC6 / 0x1CC7 | player_223c/223d setters |
| PlayerTasks | +0x1D64, 0xAC bytes | +0x1880, 0x9C bytes | ctor; wifi_user 0x1E10 -> 0x191C |
| `uniform_done` (PlayerTasks) | +0x74 | +0x66 | func_02099f14 / f2c: `adds r0,#0x74` -> `#0x66` |
| Free byte for shoes/socks (PlayerTasks pad) | +0x75 (player 0x1DD9) | +0x67 (player **0x18E7**), 1 byte | alignment pad before SaharahTask (+0x68) |
| PostOffice | block 0x1463C, 0x990 bytes, flags +0x98C | block 0x10E60, 0x580 bytes, flags +0x57C | next field 0x14FCC -> 0x113E0 |
| Free word for skin tone (PostOffice pad) | block 0x14FCA | block **0x113DE** (RAM `0x021E7536`) | pad after flags; the RAM remap agrees |
| Town grid (RAM) | `0x021E6D4C` (block 0xC354) | `0x021E04A8` (block 0xA350) | remap refs |
| Pattern size | 0x228 | 0x220 | 7 functions |

Runtime structs differ too:
- **Player actor:** fields from at least +0x385 on are 4 bytes later in JP (body handle 0x385 -> 0x389, 0x770 ->
  0x774, 0x7A0 -> 0x7A4, 0x7FC -> 0x800 in the body loader; action 0x7EC -> 0x7F0 in 54 functions; head request
  0xC90/0xC94 -> 0xC94/0xC98). Position (+0x5C/+0x64) and angle (+0x8E) are below the shift.
- **ov003 bug ("thing") slots:** slot size 0x25C -> 0x264 (2 functions); +0x204 position unchanged; +0x24D not
  confirmed.
- **ov003 item draw context** (+0x6A6C, +0x50) and the item draw loop's stack frame (+0x00/0x08/0x90/0x9C/0xD8):
  not checked yet.

## The upstairs phone (skin tone, shoes and socks)
The JP phone talk is different code, not only moved: the vtable entry AC:WW+ hooks (EU ov004 `0x02251A04` ->
`0x0222D544`) maps to a JP function with other message numbers (0x2A-0x2C) and object offsets (+0x2D0 instead of
+0x2CC). The JP Service Center lists also have one more entry (5 / 4 instead of 4 / 3; next-message lists
`0f 1b 14 17 20` / `1b 14 17 20`). This feature needs its own JP analysis: the phone talk flow, the select list
ids, free message slots in `script/JPN/` and Japanese text.

## Testing
The EU save cannot be converted (layout and text encoding differ), and `acww_save_edit.py` is EU/US only. A JP
test save has to be made in the emulator (new game: Japanese name entry, intro, first day). Its town is a new
random layout, so tests that assume the d25 town (door at unit (43.5, 55), acre 9 squares) need either grid pokes
that clear their area or positions read from the save.

## Remaining work (rough order)
1. Region-specific struct constants in the sources (named macros from a per-region header, EU values unchanged).
2. The ov003 draw context / frame offsets and the bug-slot fields.
3. JP phone talk analysis and Japanese text for the look menu.
4. A JP test save (scripted new game) and a JP save editor (pockets, bells, checksums incl. nested ones).
5. Make the tests independent of the d25 town layout, run the suites, make `acww_plus_<version>_jp.bps`.
