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
*Animal Crossing - Wild World (USA)*, game code `ADME`, rev 0, 33,554,432 bytes, CRC32 `F24508AA` (the owner's
dump; rev 1 has its own region, below). The sources and `tools/patches.py` stay in EU addresses; the US
build maps them through `tools/regions/adme.py`, which `tools/remap_region.py us` generates from the two games'
binaries (rerun it after adding or changing an address; the US build stops on any address the table lacks).
1. `py -3.12 tools/build_rom.py --release --region us` -> `build/us/acww_plus_release.nds`
2. `py -3.12 tools/run_all_tests.py --release --region us` (the tests boot the d25 save converted to the US save
   magic, `build/us/d25_us.sav`)
3. `py -3.12 tools/make_patch.py <version> --region us` -> `build/release/acww_plus_<version>_us.bps`,
   `hashes_us.txt`, `README_US.md` (from `docs/release/README_US.md`)

The US vanilla files are extracted from the dump on first use into `vanilla/ADME/extracted` of the main checkout
(git-ignored); set `ACWW_US_ROM` if the dump moves. Differences that matter: the US has 146 overlays (no EU ov018 /
ov056, so EU ov019-055 are US ov018-054 and EU ov057+ are US ov055+: the pattern editor ov123 is US ov121), arm9
and the overlay region sit about 0x1000-0x4200 lower (code home `0x0229B780`, arena-lo literal `0x02114274`), one
language (`script/ENG/`, `ftr_info/` without a language folder), and the save magic is `0x8A` instead of `0xC5`
(otherwise the save layout is the same).

## US rev 1
*Animal Crossing - Wild World (USA) (Rev 1)*, game code `ADME`, header revision 1, 33,554,432 bytes, CRC32
`7E62F586`, SHA-1 `77fde3e30e1e6068395d1f96ea63be569b61c351`. It is a rebuilt binary, so it has its own region
`us1` and address table `tools/regions/adme_rev1.py` (`tools/remap_region.py us1`): the same steps as above with
`--region us1` (outputs in `build/us1/`; patch `acww_plus_<version>_us_rev1.bps`, `hashes_us_rev1.txt`,
`README_US_REV1.md`). Its vanilla files go to `vanilla/ADME1/extracted` (`ACWW_US1_ROM` if the dump moves).
Against rev 0: 148 overlays numbered like the EU's (rev 0 drops two), every module shifted again (code home
`0x0229BDC0`, arena-lo literal `0x021147F4`, autoload 2 at `0x020E7500`), a few text files changed (none that the
hack edits), and the same save magic `0x8A`.
