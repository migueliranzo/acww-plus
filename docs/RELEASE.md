# Making a release

Releases are BPS patches against the clean EU ROM. The ROM itself is never distributed.

## Steps
1. Build the release ROM (unreleased features' hooks left out, see `RELEASE_DISABLED` in `tools/patches.py`):
   `py -3.12 tools/build_rom.py --release` → `build/acww_plus_release.nds`
2. Test it: `py -3.12 tools/run_all_tests.py --release`. Everything must pass; the sitting and lamp-switching
   tests are replaced by checks that A at a chair or a lamp does nothing.
3. Make the patch: `py -3.12 tools/make_patch.py <version>` → `build/release/acww_plus_<version>.bps` and
   `build/release/hashes.txt`. The script applies the patch again and compares the result with the release ROM.
4. Ship `acww_plus_<version>.bps`, `docs/release/README.md` and the hashes from `hashes.txt`.
5. Rebuild the dev ROM afterwards (`py -3.12 tools/build_rom.py`): both builds share `build/extracted/`.

## Base ROM
- *Animal Crossing - Wild World (Europe) (En,Fr,De,Es,It)*, game code `ADMP`, 67,108,864 bytes, CRC32 `C677970C`
  (the No-Intro dump). BPS stores this CRC, so patchers refuse any other ROM.

## What the release build leaves out (alpha, 2026-10-23)
| Feature | Why | Hooks left out |
|---|---|---|
| Sitting on outdoor seats | not tested on hardware; indoor chairs go through the same trampolines | the 12 action-table entries of actions 0x25 / 0x28 / 0x2C |
| Lamp switching | new | hook 7 (`0x0200FAF0`, the outdoor A handler) |

Their code is still in the ROM but never called: with the hooks left out, the game runs its own code there. The
code home (`docs/features/code_home.md`) stays, because outdoor furniture loads its models through it.

## Patch size
About 1 MB, mostly the re-compressed `arm9` and patched overlays (any code change re-packs the whole compressed
binary). Building them uncompressed would shrink the patch but cost about 12% of the ARM9 in town
(`docs/OPTIMIZATION_REPORT.md`), so they stay compressed.

## US version
Not supported: the hack uses EU addresses everywhere (54 patch sites, ~130 code and data addresses, plus the build
constants). A US port needs a US dump and a remap of those addresses; see the 2026-10-23 notes in `PROGRESS.md`.
