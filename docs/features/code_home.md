# Code home: an autoload block below the main arena

Status: **done** (2026-10-20, verified headless). Sources: `src/code_home.h`, `src/heap/*.c`; build: `build_heap_code`
in `tools/build_rom.py`. Test: `tools/test_code_home.py`.

## Why
The ITCM payload (`0x01FFDC00..0x02000000`) had ~400 bytes left. Code that isn't per-frame hot, or doesn't fit,
goes here.

## How it works (arena-lo shift)
- Memory map: the main BSS (autoload 3 in vanilla) ends at `0x02203D20`, where the overlay slots start. The highest
  overlay, ov098, ends at **`0x0229F9A0`**. That is `SDK_MAIN_ARENA_LO`: `OS_InitArena` starts the main arena there,
  and the game builds its root heap from that arena. `boot_fill_overlay_region_trap` fills
  `[ov000 start, 0x0229F9A0)` with `0xE7FEE7FE` (its own literal at arm9 `0x020B0FA4`, left unchanged).
- The build patches the SDK literal at `0x02117BD8` (in autoload 2, base `0x020E8180`): `0x0229F9A0 → 0x022A19A0`
  (+`HEAP_CODE_RESERVE` = 8 KB). The root heap now starts 8 KB higher, and `0x0229F9A0..0x022A19A0` belongs to us.
- `src/heap/*.c` is compiled as a second unit and linked at `0x0229F9A0` + export table. Calls to the game and to
  the ITCM payload are plain BLs (all within ±4 MB). There are no relocations.
- The block ships as an **extra autoload**: the crt0 copies it in at boot, before `main`, like the ITCM payload,
  and flushes the caches as it does for every autoload. It needs no file, no runtime allocation and no lifetime
  handling: it is there in every scene, from boot to power-off.
- **Autoload order matters.** dsd orders autoloads by index, and the crt0 handles them in that order. The vanilla
  autoload 3 is the main BSS clear (`0x0213FAA0..0x02203D20`, 0xC4280 bytes). That range covers where the new
  block's source data sits in the loaded arm9 image (`0x021473FC..`). So the new block takes index 3 and the BSS
  clear becomes index 4. The game's autoload callback (`0x02000E58`) is a bare `bx lr`, so nothing else looks at the
  indices. Check the order with `tools/analysis/arm9_autoloads.py build/acww_plus.nds`.
- Layout at `0x0229F9A0`: `'AWHP'`, then export pointers (the `HX_*` slots in `src/code_home.h`, in the order of
  `HX_EXPORTS` in `tools/build_rom.py`), then code and data. `hx_ready()` checks the magic.

## Why not a heap block (the first version, commit 9cc81c9)
That version loaded `/zplus/code.bin` into a root-heap block on first use, with relocations and an I-cache
invalidate. It worked, but it needed a runtime allocation that could fail, a 64 KB free-block check, a new NitroFS
file, and a guard against the block going stale if the heap were rebuilt. The arena shift costs the same RAM
(the heap is 8 KB smaller instead of 2.6 KB being allocated from it) and has none of those cases.

## What lives there
| Export | From | Size |
|---|---|---|
| `hx_claim_vram`, `hx_can_place`, `hx_load_model` | outdoor furniture model loading (file reads, texture halving, VRAM arena search, eviction) | ~2.5 KB |
| `hx_is_seat_model`, `hx_sit_request`, `hx_sit_start`, `hx_sit_tick` | sitting on outdoor seats (`src/heap/sit.c`) | ~0.6 KB |

Hot per-frame code (draw, collision, coverage) stays in ITCM (no wait states).

## Budget (2026-10-20)
- ITCM payload: 7.9 KB, **~1.1 KB free** (after lamp switching and the sit trampolines).
- Code home: 3.2 KB of the 8 KB reserve used, **~4.9 KB free**. Raise `HEAP_CODE_RESERVE` if needed: each KB comes
  out of the root heap.

## Needs a hardware check
- The root heap is 8 KB smaller. The game's own large allocations (scene loads, the museum, Nook's) should be
  tried on the flashcart. Our model cache already refuses loads below 48 KB free.
