# AC:WW+ reference map (read-only sources)

Target: Animal Crossing: Wild World, EU `ADMP`. **Never write into `C:\NDS_RECOMP` or `E:\claudeGameDecomp`.**
Abbreviations: `RUNS` = `C:\NDS_RECOMP\prototype\runs`, `CGD` = `E:\claudeGameDecomp`.

## Build inputs
- Vanilla ROM: `CGD\0389 - Animal Crossing - Wild World (E)(Legacy).nds`. Extracted copy: `CGD\extracted\` (the build copies from here).
- dsd (ROM unpack/build): `CGD\dsd-windows-x86_64.exe` (`rom build --config ... --rom ...`).
- mwccarm: `C:\NDS_RECOMP\nds-docs\pokemon_dp\sdk\cw\ARM_Tools\Command_Line_Tools\mwccarm.exe`. It needs `LM_LICENSE_FILE=...\pokemon_dp\sdk\cw\license.dat`, which `tools/build_rom.py` sets.

## Names / symbols (newest = best)
- **Namestore** (21.5k of 29.3k functions named, dsd format): `RUNS\2026-10-15-u0\namestore\arm9\symbols.txt`, `...\overlays\ovNNN\symbols.txt`, `itcm\`, `dtcm\`.
- SDK names: `C:\NDS_RECOMP\prototype\docs-index\sdkmatch\acww_sdk_names.tsv`.
- C types header: `CGD\tools\ghidra\acww.h`.

## Decompiled C (grep it; don't read whole files)
- Whole game: `RUNS\2026-10-15-u0\u1\gh\all.ann`. Uses old names; grep by `func_<addr>` / `func_ovNNN_<addr>`.
- Main module, current names: `RUNS\2026-10-16-naming\wave{1,2,3}\R{1..6}\region.c` and `region_lit.c`, plus `GLOSSARY.md` (struct offsets). Ranges are in `RUNS\2026-10-16-naming\regions.tsv`.
- ov003 (town): `RUNS\2026-10-16-night\N4\work\ov003.c` (+ `funcs.tsv`, `h00-h07.md`).
- ov004 (indoor): `RUNS\2026-10-16-night\N3\work\ov004.c` (+ `ov004_classes.json`).
- Menus ov090-ov146: `RUNS\2026-10-16-night\N5\dec\`. Annotated copies: `N5\work\HP\res\` (ov094 pocket base, ov096 pockets, ov097 indoor item actions, ov098 outdoor item actions).
- ov002 (UI library): `RUNS\2026-10-16-night\N5\dec2\ov002.c`.

## Schemas / data
- Items: `RUNS\2026-10-15-u0\u4a\items.json` (+ `frag\items.md`). Town: `u2\town_schema.json`.
- Save: `RUNS\2026-10-16-night\N1\save_schema_v2.json`.
  - RAM = block offset + `0x021DA9F8`.
  - Player p starts at block `0xC + 0x228C*p`.
  - Checksum is at `+0x15FDC`.
- Overlays: `RUNS\2026-10-16-night\N1\overlay_map_v2.tsv`. Slots, scenes and menus: `RUNS\2026-10-15-u0\u3\README.md`, `scene_table.tsv`, `menu_table.tsv`, `profiles.tsv`.
  - Empty, never-loaded overlays: ov000, ov057-064, ov089.
- Player actions: `RUNS\2026-10-16-night\N2\action_table.json`.
- Time, weather and the daily update: `RUNS\2026-10-16-night\N6\` (`clock.json`, `weather.json`, `daily_update.json`, `save_format.json`).
- Economy: `RUNS\2026-10-15-u0\u4a\frag\` (`nook.md`, `money.md`, `vendors.md`, `money_turnip_weeks.json`).
- Villagers: `u4b\`. Critters, museum, mail and patterns: `u4c\`.
- Text: BMG files in `files/script/<LANG>/`. Parser: `RUNS\2026-10-15-u0\u4b\tools\bmg.py`.

## Topic address books (CGD)
- `CGD\docs\INDEX.md`. The `ADDRESSES-ARM9-*.md` books cover POCKET, PLAYER, PAD, TOWN, ITEMS, TEXT and more; there are also `GAME-HOUSE-*`, `GAME-VILLAGER-*` and `GAME-THING-*`.

## Testing
- Emulator: `C:\NDS_RECOMP\ndsref\build-native\ndsref.exe`. Debug client: `C:\external\ndsrecomp\oracle\_client.py`.
  - Command reference: `C:\NDS_RECOMP\prototype\04-tcp-command-reference.md`.
  - Useful commands: `run_to_event`, `run_to_pc`, `read_region`, `framebuffer`, `keys`, `touch`, `regs`.
  - There is no `write_mem` on ndsref.
- Save editor: `C:\NDS_RECOMP\animalcrossingwwrecomp\tools\acww_save_edit.py`. Test saves: `animalcrossingwwrecomp\scenarios\saves\d25*.sav`. Scenarios: `animalcrossingwwrecomp\scenarios\*.json`.
- Harness pattern: `tools/test_outdoor_furniture.py`.

## SDK / hardware docs
- `C:\NDS_RECOMP\prototype\docs-index\sdkman\` has the NitroSDK-3.1 and NitroSystem man pages as markdown. Search them with `prototype\tools\ndsdocs.py`.
- GBATEK as markdown: `C:\NDS_RECOMP\prototype\docs-index\gbatek\`.
- Player's guide (game facts): `C:\NDS_RECOMP\acww-docs\`.

## Code space (our own notes)
- Current payload: ITCM tail at `0x01FFDC00`, ~9 KB usable up to `0x02000000`. The payload is 1.7 KB so far.
- Larger features will need another cave. Candidates: an empty overlay id, or main-RAM arena space. Not investigated yet.
