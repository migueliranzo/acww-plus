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
- **Our harness:** `tools/harness.py`.
  - `Emu` context: boot, keys, touch, `read_mem`, screenshots.
  - `prepare_save` writes save pokes and grid items and fixes the checksums.
  - `walk_until` walks closed-loop to a coordinate.
  - Player position helpers.
- Tests: `tools/test_*.py`; all of them via `tools/run_all_tests.py`. Probes: `tools/probes/`.
- Timing facts (ndsref):
  - Game logic runs about every 2–3 vblanks.
  - A key held under ~3 vblanks can be missed; use hold ≥ 6.
  - Walking covers about 1 unit per 35 frames.
  - The boot to town (`boot_to_town`) ends near v6950, with the player on the doorstep at unit (43.5, 55.0). Acre 9 local (lx, lz) = global (32 + lx, 48 + lz).

## Our build tooling
- `tools/build_rom.py`:
  - unity-compiles `src/*.c`, links at ITCM `0x01FFDC00`, writes `build/payload.map`
  - recopies vanilla binaries
  - applies `tools/patches.py` (bl / bytes / ptr / dptr, each checked against the vanilla bytes)
  - applies `tools/file_patches.py` (NitroFS edits, restored from vanilla on every build)
- `src/acww.h`: shared types and addresses.
- `tools/bmg_tool.py`: BMG reader and writer with an LZ10 / 0xF7-chunked compressor (byte-identical rebuilds).
- `tools/analysis/`:
  - `fn.py` prints a decompiled function by name or address from the reference decomps
  - `find_bl.py` lists Thumb BL call sites
  - `nitro_tex.py` lists and renders TEX0 textures and palettes
- **Never write through `build/extracted/files` as a junction.** It used to point into `E:\claudeGameDecomp`; it is a real copy now.

## SDK / hardware docs
- `C:\NDS_RECOMP\prototype\docs-index\sdkman\` has the NitroSDK-3.1 and NitroSystem man pages as markdown. Search them with `prototype\tools\ndsdocs.py`.
- GBATEK as markdown: `C:\NDS_RECOMP\prototype\docs-index\gbatek\`.
- Player's guide (game facts): `C:\NDS_RECOMP\acww-docs\`.

## Code space (our own notes)
- **ITCM payload:** ITCM tail at `0x01FFDC00`, ~9 KB usable up to `0x02000000`. The payload is **6.4 KB**, with ~2.8 KB
  left (2026-10-20). Keep per-frame hot code here.
- **Code home (2026-10-20):** `0x0229F9A0..0x022A19A0` (8 KB), the start of the SDK main arena, moved up by patching
  the SDK literal at `0x02117BD8`. `src/heap/*.c` is linked there and shipped as an extra autoload (index 3; the main
  BSS clear becomes index 4). ~5.5 KB free. Details and reasoning: `docs/features/code_home.md`.
  - Chosen over a root-heap block loaded from a file (commit 9cc81c9): same RAM cost, but no runtime allocation, no
    relocation, no lifetime handling.
- Memory map facts: main BSS `0x0213FAA0..0x02203D20`, then the overlay slots (ov001 at `0x02203D20`); the highest
  overlay end is ov098's, `0x0229F9A0` (= the vanilla main arena lo). Boot fills the overlay region up to there with
  `0xE7FEE7FE` traps (`boot_fill_overlay_region_trap`).
- Ruled out: `unk_autoload_3` (it is the main BSS); DTCM (not executable); empty overlays without a free RAM range.
- Other candidates if ever needed: a bigger arena shift (each KB comes out of the root heap); ov003's tail slack
  (0x238 bytes).

## Free save space we use
- PostOffice `pad_98e` (block `0x14FCA`): skin base tone, 4 bits per player.
- PlayerTasks `pad_75` (player +0x1DD9): shoe and sock colours. Player +0x1DDA / +0x1DDB are still free.
- Header `unknown_0001` (block +1): free, never written.
