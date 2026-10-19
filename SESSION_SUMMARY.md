# AC:WW+ "Place Furniture Outside" ROM Hack - Session Summary

**Date:** 2026-10-18  
**Project Directory:** [`e:\acww-plus`](file:///e:/acww-plus)  
**Target Game:** *Animal Crossing: Wild World* (Nintendo DS, European release `ADMP`)  
**Reference Trees (Read-Only):** `C:\NDS_RECOMP` and `E:\claudeGameDecomp`  

---

## 1. Session Purpose & Overview

The user previously started an ARM-to-C game recompilation project for *Animal Crossing: Wild World* to run on PC. Because full decompilation or recompilation to a DS homebrew target involves immense time investment, the user wanted to explore creating a **ROM Hack / ROM Mod** to implement a specific, highly desired feature: **placing furniture outside** (like modern titles such as *Animal Crossing: New Horizons*), while keeping the game 100% playable on real Nintendo DS hardware and flashcarts/emulators.

This session aimed to:
1. Clarify how a ROM hack differs fundamentally from decompilation and recompilation.
2. Investigate the technical feasibility, memory constraints, and architecture of rendering and managing outdoor furniture in the DS hardware environment.
3. Build a reproducible, isolated build and testing environment in [`e:\acww-plus`](file:///e:/acww-plus) using Metrowerks CodeWarrior C compiler (`mwccarm.exe`), linking into unused ITCM memory and patching overlay/arm9 binaries.
4. Implement and verify the 4 required hooks for full 3D rendering, scene teardown, collision, and pocket dropping.

---

## 2. Goals & Status Breakdown

### A. Goals Completed

1. **Architectural Analysis & Research:**
   - Explained ROM Hack vs Decomp vs Recomp concepts and trade-offs.
   - Analyzed VRAM allocations on the DS (Texture VRAM Banks A/B/C) and established that outdoor town scenes have ample free VRAM slots (~40 KB) when using a shared dynamic LRU cache.
   - Located unused ITCM RAM (`0x01FFDC00..0x01FFE2D4`, 1,748 bytes) where injected C code can execute at maximum CPU speed without touching main RAM code pages.

2. **C Toolchain & ROM Build Pipeline ([`build_rom.py`](file:///e:/acww-plus/tools/build_rom.py)):**
   - Implemented automated compilation using CodeWarrior `mwccarm.exe` (`-O4,s -proc arm946e -thumb -interworking`).
   - Implemented an ELF object parser and linker that applies `R_ARM_ABS32` and `R_ARM_THM_CALL` relocations at `0x01FFDC00`.
   - Created automated binary patchers for:
     - `itcm.bin` & `itcm.yaml` (reserves ITCM space).
     - `ov003.bin` (outdoor town overlay hooks for rendering, teardown, and collision shape).
     - `arm9.bin` (main binary hook for outdoor drop item orientation).
   - Packaging via `ds-decomp` (`dsd.exe rom build`) producing [`e:\acww-plus\build\acww_plus.nds`](file:///e:/acww-plus/build/acww_plus.nds) (67 MB) in ~6 seconds.

3. **C Patch Core Implementation ([`outdoor_furniture.c`](file:///e:/acww-plus/src/outdoor_furniture.c)):**
   - **`OutdoorFtrCache`:** 6-slot LRU cache managing dynamic `.nsbmd` / `.nsbtx` models loaded directly from ROM `/ftr/` archives.
   - **Curved Drum Rendering:** Copies town drum world matrix into `mdl_obj + 0x64` so furniture items follow the spherical horizon curve of the town.
   - **Lighting & Emission:** Synchronizes outdoor time-of-day lighting via `FN_LIGHT_SLOT2_TO_EMI()` and `FN_NNS_G3D_SET_EMI_ALL()`.

4. **Hook 1 (3D Outdoor Rendering) - 100% Verified:**
   - Hooked `ov003::0x022212C0` -> `hook_ov003_draw_item` @ `0x01FFDCE4`.
   - Category 3 & 4 items (`0x3000..0x4BA3`) render as genuine 3D models with proper 4-way rotation (`item & 3`).
   - Captured proof in [`02_all_six_furniture_settled_v07158.png`](file:///e:/acww-plus/build/screenshots/02_all_six_furniture_settled_v07158.png), showing:
     - Exotic Chair (`0x3011`, facing East 90°)
     - Exotic Table (`0x3014`, facing South 0°)
     - Exotic Lamp (`0x301C`, facing South 0°)
     - Ranch Armchair (`0x303B`, facing West 270°)
     - Classic Clock (`0x3074`, facing South 0°)
     - Duplicate Exotic Chair (`0x3013`, facing West 270°, sharing cached model slot in VRAM!)
   - Verified zero leaf icons; stable 30 fps in `ndsref.exe`.

5. **Hook 3 (Outdoor Collision & Ground Interaction) - 100% Verified:**
   - Hooked `ov003::0x02223586` -> `hook_ov003_item_shape_lookup` @ `0x01FFDC48`.
   - Returns a solid collision cylinder (`{0x0C, 0x10, 0x06, 0x00}`) for outdoor furniture.
   - Captured proof in [`03_collision_with_exotic_table_v07266.png`](file:///e:/acww-plus/build/screenshots/03_collision_with_exotic_table_v07266.png) and [`04_collision_against_chair_v07251.png`](file:///e:/acww-plus/build/screenshots/04_collision_against_chair_v07251.png).
   - Player solidly bumps against furniture without clipping; ground item labels (e.g. `"exotic table"`) display properly on approach.

6. **Engine Internals & Hook 4 Reverse Engineering:**
   - Fully traced pocket menu execution flow (`ov096`, `ov098`, `ov002`).
   - Identified that `func_02042d8c` receives `player_idx` (0..3) as `param_1`, not the actor pointer.
   - Discovered `FN_GET_PLAYER_ACTOR(4)` (`0x02095550 | 1`) to retrieve the actual actor structure and read angle at `+0x8E`.
   - Updated [`src/outdoor_furniture.c`](file:///e:/acww-plus/src/outdoor_furniture.c) with this fix.

---

### B. Goals In-Progress / Not Completed

1. **Automated Outdoor Drop Verification in `test_outdoor_furniture.py`:**
   - In [`05_menu_drop_on_ground_selected_v07808.png`](file:///e:/acww-plus/build/screenshots/05_menu_drop_on_ground_selected_v07808.png), the pockets menu successfully selected `"Drop on Ground"`.
   - However, the drop failed in engine logic (`"There's no room to put things here!"`) because the player was positioned in a tight bottleneck between the town signboard, snow cliff, and the placed Exotic Chair. `func_020308e0` checks a collision cylinder of radius `0x19` (~1.5 tiles), which collided with the surrounding objects.
   - Moving the player slightly further south into open dirt will resolve this clearance check.

2. **Hook 2 Teardown Lifecycle Verification:**
   - `hook_ov003_teardown` is compiled, linked at `0x01FFDC74`, and hooked at `ov003::0x02220ADA`.
   - Need to trigger an outdoor-to-indoor scene transition (e.g., walking back into the player's house) and assert that `s_cache` is freed and reset to null.

---

## 3. Where the Job Was Stopped

The session was paused right after:
1. Resolving the player actor pointer bug in `hook_outdoor_drop_item` ([`src/outdoor_furniture.c`](file:///e:/acww-plus/src/outdoor_furniture.c)), changing it to fetch `actor = FN_GET_PLAYER_ACTOR(4)`.
2. Discovering the exact reason the pocket drop rejected placement (unobstructed clearance radius `0x19` in `func_020308e0`).

### Next Immediate Actions to Resume:
1. Rebuild ROM with `py -3.12 tools/build_rom.py`.
2. In [`tools/test_outdoor_furniture.py`](file:///e:/acww-plus/tools/test_outdoor_furniture.py), adjust the player movement to walk further south onto wide-open dirt before opening pockets and dropping the Classic Chair (`0x305C`).
3. Add a step to walk back to the doorstep (`0x0D64A`), enter the house (`ov004`), and assert `s_cache == 0` (verifying Hook 2).
4. Package the final screenshots and documentation.
