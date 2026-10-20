# Code home: heap-loaded code file

Status: **done** (2026-10-20, verified headless). Sources: `src/code_home.c` (loader, ITCM), `src/heap/*.c` (the
code that lives there). Test: `tools/test_code_home.py`.

## Why
The ITCM payload (`0x01FFDC00..0x02000000`) had ~400 bytes left. Code that isn't hot or that doesn't fit now goes
into a NitroFS file that is loaded into main RAM once.

## How it works
- **Build** (`tools/build_rom.py`, `build_heap_code`): `src/heap/*.c` is compiled as a second unit and linked at
  address 0 by our own linker. Symbols it uses from the ITCM payload (e.g. `g_ftr_perf`) resolve to their fixed
  addresses. Every ABS32 word that points inside the image goes into a relocation list. A direct call (BL) out of
  the image is a build error: the image calls the game and the ITCM payload only through absolute pointers.
- **File** `/zplus/code.bin` = `{ 'AWHP', image size, export count, reloc count, export offsets[], reloc
  offsets[], image }`. It is listed last in `path_order.txt` (dsd gives unlisted files an empty FAT entry). It gets
  the last file id (17124); every vanilla id keeps its path (`tools/analysis/fnt_ids.py VANILLA ROM`).
- **Loader** `hx_ready()`: on first use, if the root heap's largest free block is at least 64 KB, it loads the file
  with the game's `file_load_alloc` (align -32, i.e. from the heap's tail), adds the image address to each
  relocated word, writes the data cache back (`DC_FlushRange`) and invalidates the instruction cache
  (`IC_InvalidateRange`) over the image, and fills `g_hx_fn[]`. The block stays for the whole session (2.6 KB).
  Each call re-checks the header magic; if the block was overwritten, it loads again.
- **Fallback:** if the load is refused, `hx_ready()` stays 0 and the features that need it fall back to vanilla
  (outdoor furniture shows leaves).
- Exports: `HX_EXPORTS` in `tools/build_rom.py`, matching the `HX_*` slots in `src/code_home.h`.

## What lives there
| Export | From | Size |
|---|---|---|
| `hx_claim_vram`, `hx_can_place`, `hx_load_model` | outdoor furniture model loading (file reads, texture halving, VRAM arena search, eviction) | ~2.5 KB |

Hot per-frame code (draw, collision, coverage) stays in ITCM.

## Budget after the move (2026-10-20)
- ITCM payload: 6.7 KB, **~2.5 KB free**.
- Heap code: 2.6 KB. Room is limited only by the heap; keep the file small (each KB is a KB less for the game).

## Needs a hardware check
- The cache maintenance (flush + I-cache invalidate) matters only on hardware; melonDS-based ndsref has no caches.
- Loaded at the first outdoor furniture draw. It is taken from the heap's tail, which the game also uses for
  temporary loads.
