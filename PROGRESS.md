# AC:WW+ progress log

Feature list from the owner (2026-10-19). Per-feature notes live in `docs/features/`. Reference map: `docs/REFERENCES.md`.
Build: `py -3.12 tools/build_rom.py` → `build/acww_plus.nds`. Headless tests: `tools/harness.py` (+ `tools/test_*.py`).

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Furniture can be placed outdoors | **done** | `docs/features/outdoor_furniture.md` |
| 2 | Patterns can use transparency | todo | |
| 3 | Skin tone can be changed on the attic phone | todo | |
| 4 | Sock / shoe color variations | todo | |
| 5 | Trees can be shaken with a net or fishing rod equipped | todo | |
| 6 | Tools swapped / put away with L/R | todo | |
| 7 | Monkeys (Champ, Nana, Simon, Tammi, Monty, Elise) obtainable | **done** (untested in play) | `docs/features/monkeys.md` |
| 8 | Nookington's without multiplayer | **done** (untested in play) | `docs/features/nookingtons.md` |

## Log
- 2026-10-19:
  - Set up git.
  - Replaced the `build/extracted/files` junction (it pointed into the read-only reference tree) with a real copy.
  - Fixed the CodeWarrior license path.
  - Outdoor furniture finished:
    - pooled VRAM model cache with distance priority
    - multi-square footprints with 0xF031 markers and solid collision; the collision hook had been on the wrong function (a tree-shake class vtable), now moved to the real query
    - footprint-aware drop spots
    - teardown verified
