# AC:WW+ progress log

Feature list from the owner (2026-10-19). Per-feature notes live in `docs/features/`. Reference map: `docs/REFERENCES.md`.
Build: `py -3.12 tools/build_rom.py` → `build/acww_plus.nds`. Headless tests: `tools/harness.py` (+ `tools/test_*.py`).

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Furniture can be placed outdoors | **done** (+ sitting, lamps, tree drops stay leaves) | `docs/features/outdoor_furniture.md` |
| 2 | Patterns can use transparency | **done** (editor UI untested) | `docs/features/pattern_transparency.md` |
| 3 | Skin tone can be changed on the attic phone | **done** | `docs/features/skin_tone.md` |
| 4 | Sock / shoe color variations | **done** | `docs/features/shoes_socks.md` |
| 5 | Trees can be shaken with a net or fishing rod equipped | **done** | `docs/features/tree_shake.md` (bug-nearby exception untested) |
| 6 | Tools swapped / put away with L/R | **done** | `docs/features/tool_swap.md` |
| 7 | Monkeys (Champ, Nana, Simon, Tammi, Monty, Elise) obtainable | **done** (untested in play) | `docs/features/monkeys.md` |
| 8 | Nookington's without multiplayer | **done** (untested in play) | `docs/features/nookingtons.md` |

## Overnight summary (2026-10-19)
- All 8 features are implemented and committed. The full headless suite `tools/run_all_tests.py` passes 18/18 on the final ROM.
- **Please check by hand:**
  1. **Pattern editor (Able Sisters):** L/R should cycle … 15 → transparent → 1. Paint some transparent pixels, then lay the design on the ground.
  2. **Net + bugs on a tree (summer):** the net should still swing at a bug on the trunk. A tree with no bug nearby should shake.
  3. **Walked-upstairs phone (not the wake-up screen):** the menu should be Set sound / Change my look / Downloads / Nothing.
  4. **Change my look:** watch the shoes and socks change while standing on the phone (live refresh). Only the wake-up screen was tested, where the feet are under the covers.
  5. **Monkeys and Nookington's:** the play tests you planned.
  6. **Real hardware:** furniture model uploads wait for VBlank, and the body and palette refreshes go through the game's VBlank queue. A flashcart run is still the real proof.
- **Known limits:**
  - About 5 large-texture furniture models can show at once. Farther pieces show leaves until you walk closer.
  - Outdoor furniture can't be interacted with (no sitting).
  - New text is English in all languages.
- **Code space:** the ITCM payload is 6.6 KB, with about 2.5 KB free. `docs/REFERENCES.md` lists the next places to look for more.
- **Save use:** PostOffice pad (skin base tone) and PlayerTasks pad +0x1DD9 (shoe and sock colours). Both are 0 in vanilla saves.

## Session summary (2026-10-20, outdoor furniture follow-ups)
- **Fixed:** the invisible solid square left where a 2-square piece's second square was, after a pickup (seen on
  hardware). The coverage list went stale once nothing was drawn. Regression test: `test_furniture.py ghost`.
- **New:**
  - Furniture shaken out of a tree stays a leaf; only player-dropped furniture is 3D (RAM only: an unpicked tree
    drop shows 3D after a reload).
  - A with empty hands switches a lamp's shade off (dark) and back on. (A night "glow" was tried; it can't show,
    see `docs/features/outdoor_furniture.md`.)
  - A sits on chairs, benches and sofas (d-pad / B to stand up).
  - Code home: an 8 KB block at `0x0229F9A0` below the moved SDK main arena (`docs/features/code_home.md`).
- **Please check on the flashcart:**
  1. Pick up a beach chair or bench outdoors: no invisible block left behind.
  2. Shake a tree with furniture in it: a leaf, not a 3D model.
  3. A with empty hands, facing a lamp: its shade goes dark; A again: back to normal.
  4. Sitting outdoors: the pose looks right; d-pad or B stands up. Also sit on a chair **indoors**: the indoor sit
     actions now go through trampolines (not covered by the headless tests).
  5. The root heap is 8 KB smaller: visit the museum, Nook's, a few houses.
- **Known limits:** no sound for lamp switching or sitting outdoors; no lying on beds outdoors; sitting is off while
  other players are in town.

## Alpha release (2026-10-23)
- Release build: `tools/build_rom.py --release` leaves out sitting and lamp switching (hooks only; see
  `docs/RELEASE.md`). `tools/run_all_tests.py --release`: 25/25. Patch: `tools/make_patch.py alpha1` →
  `build/release/acww_plus_alpha1.bps` (1.08 MB, BPS, base CRC32 C677970C, self-checked). Player README:
  `docs/release/README.md`.
- Owner flashcart checks passed: tree drops land as leaves; no ghost square after picking up a 2-square piece.
- **US version:** not supported. A port needs a US dump (none in the reference folders) and a remap of 54 patch
  sites, ~130 code/data addresses and the build constants (ITCM payload, arena literal, autoload base, action
  tables), plus a US test save for the harness. Most of the remap could be done by matching EU function bytes in
  the US binary. Estimate: a few sessions, then a full test pass.

- **Both regions released as alpha1 (2026-10-23):** EU `acww_plus_alpha1.bps` (base CRC32 C677970C, hardware-tested
  by the owner) and US `acww_plus_alpha1_us.bps` (base ADME rev 0, CRC32 F24508AA, emulator-tested only: --release
  suite 25/25 on both). The US port maps the EU addresses through `tools/regions/adme.py` (`tools/remap_region.py`).

- **US rev 1 added to alpha1 (2026-10-25):** `acww_plus_alpha1_us_rev1.bps` for *Animal Crossing - Wild World (USA)
  (Rev 1)* (base CRC32 7E62F586, patched ROM CRC32 15BCB2C5). Rev 1 is a rebuilt binary with its own region `us1`
  and table `tools/regions/adme_rev1.py`; dev suite 29/29, --release suite 25/25, emulator only. The rev 0 patch
  is unchanged.
- **Japanese version: deferred to the beta (2026-10-25).** Addresses map (`tools/regions/admj.py`), but the save,
  player and actor layouts and the phone menu differ; findings and plan in `docs/research/jp_port.md`.

## QOL pack (2026-10-27, EU only)
- Bell bags picked up stack onto a pocket bag (100 + 100 → 200), wallet untouched.
- Fruit stacks up to 9 in one slot ("2 apples" .. "9 apples"); eating or planting takes one, Nook pays per fruit.
- Blathers: X marks several items in his picker (green ring); he then takes them one after another (donations and
  fossil assessments) without reopening the pockets.
- Nook's sale day, evening sale and spotlight item now also happen in one-player towns.
- Notes: `docs/features/qol_pack.md`. Tests: `tools/test_qol.py` (in `run_all_tests.py`). US addresses not mapped.

## Log
- 2026-10-22: lamp switching reworked (shade goes dark when off): the emission-based version changed nothing on
  screen (owner report). Night glow removed.
- 2026-10-20: ghost-square fix, tree drops stay leaves, lamp glow, code home (heap file first, then the arena
  shift), lamp switching, sitting. Suite 29/29.
- 2026-10-19:
  - Set up git.
  - Replaced the `build/extracted/files` junction (it pointed into the read-only reference tree) with a real copy.
  - Fixed the CodeWarrior license path.
  - Outdoor furniture finished:
    - pooled VRAM model cache with distance priority
    - multi-square footprints with 0xF031 markers and solid collision; the collision hook had been on the wrong function (a tree-shake class vtable), now moved to the real query
    - footprint-aware drop spots
    - teardown verified
