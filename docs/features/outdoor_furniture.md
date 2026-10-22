# Feature: furniture can be placed outdoors

Status: **done** (verified headless on ndsref, 2026-10-19). Source: `src/outdoor_furniture.c`. Test: `tools/test_furniture.py [collide|drop|house|pickup|marker]`, or `ghost` / `treedrop` / `lampuse night|day` / `sit chair` / `sit bench` alone.

## What the player sees
- Furniture dropped outdoors from the pockets ("Drop on Ground") is drawn as its real 3D model, not a leaf.
- **A with empty hands, facing a lamp,** switches it off: its shade (the model's `lp_m…` materials) turns dark
  grey. A again switches it back on. Lamps are on (vanilla look) until switched. 16 switchable models: the
  light-source models of `ftr_info/indoor.bin` (byte 1 bits 4/5) that have a shade material; the festive candle has
  none. The switch is kept per square in RAM (8 lamps) until the lamp is picked up; after a save and reload every
  lamp is on again. No sound: the indoor lamp switch sounds (0x498 / 0x499) froze the game when played in town,
  presumably because their sound bank isn't loaded there. Evidence: `ftru_night_80` / `81` / `82`.
  - **No "glow".** A lamp can't be made brighter than vanilla this way: the GPU multiplies the texture by the lit
    colour, which is already about white day and night. The first version raised the emission at night and when
    switched; the test passed on the material value, but nothing changed on screen (even a pure-blue emission didn't
    show). Found 2026-10-22 from the owner's report; the test now compares pixels around the lamp.
- **Sitting:** A with empty hands, facing a chair, bench, sofa or couch (either square of a 2-square piece),
  sits the player on that square, turned the way the piece faces. The d-pad or B stands them up, back where they
  stood. 59 seat models (dma.bin behaviour kinds 0x08 / 0x26 / 0x2C, the indoor chair class). Not offered while
  other players are in town. Beds (lying down) are not done. Evidence: `ftrs_chair_90_sitting`.
- Furniture shaken out of a tree stays a leaf (vanilla look, not solid, no markers) until picked up. RAM only: after a
  save and reload, an unpicked tree drop shows as 3D furniture (owner's choice, 2026-10-20).
  - It uses the town's curved-drum matrix and time-of-day lighting.
  - It faces the way the player faced when dropping it (4 directions).
- Furniture is solid. Multi-square pieces block their whole footprint:
  - 2-square pieces (benches, tables, couches) along their rotated long axis
  - 2×2 pieces (beds, big tables)
- A multi-square drop needs all its squares free. Otherwise the game's normal spot search tries the next candidate, then shows "There's no room…".
- Picking up works as in vanilla: B on or next to the anchor. Marker squares are never picked up.

## How it works
| Hook | Where | What |
|---|---|---|
| 1 | ov003 `0x022212C2` (item draw loop, category 1/3/4 branch) | Draws furniture from the model cache. Falls back to the vanilla icon. |
| 2 | ov003 `0x02220ADA` (scene teardown) | Frees the cache (heap). |
| 3 | arm9 `0x020B2A90` (`town_query_item_shape` → `ov003_item_shape`) | Collision cylinders for furniture and 0xF031. Writes missing markers, clears orphaned ones. |
| 4 | arm9 `0x02042DB4` (outdoor drop) | Puts the player's facing into `item & 3`. Flags a furniture drop in progress. |
| 5 | arm9 `0x02042B7A` (`field_put_spot_find` → `field_put_spot_check`) | During a furniture drop, a spot passes only if every footprint square passes. |
| 6 | arm9 `0x02044CEA` (`tree_shake_nonfruit_drop` → item-put request `0x020457B4`) | Remembers the square of tree-dropped furniture (`s_leaf`, 8 squares). Draw and collision treat those squares as vanilla. An entry is dropped once its square no longer holds furniture (checked each drawn frame and before every player drop). |
| 7 | arm9 `0x0200FAF0` (`player_act_on_target_dispatch` → ov003 A handler, every logic frame) | On an A press (KEYINPUT edge) with empty hands, a lamp in front is switched, or a seat in front is sat on, instead of the vanilla handler. |
| 8 | arm9 action tables (12 pointers: start/tick/exit/remote of actions 0x25, 0x28, 0x2C, e.g. `0x020D7074`) | Trampolines: indoors (`*0x020E4E00 == 1`, ov004 loaded) the ov004 handler runs; in town our sitting (`src/heap/sit.c`). |

- **Footprints** come from the game's own helper: `furniture_footprint_ctor/count/square` (`0x02052664/48/E8`). This is the same table the house rooms use.
  - Secondary squares hold **0xF031**, the house-room "second square of a furniture piece" id.
  - The game treats 0xF031 as a special, non-pickable id (`item_is_special_slot_id`).
  - Markers are written lazily by the collision hook, when the anchor or the secondary square is queried, so no drop-completion hook is needed.
  - An 0xF031 with no covering anchor (after a pickup) is reset to 0xFFF1 the first time anything walks near it.
  - "Covering anchor" means: a piece drawn this or the last frame listed the square (coverage list), **and** that anchor
    square still holds furniture. The anchor check was added on 2026-10-20 after a ghost seen on a real DS: once the
    last piece in view was picked up, nothing was drawn any more, so the coverage list never turned over and kept its
    second square solid (and even re-marked it). Placing a piece elsewhere made the list turn over, which is why the
    old ghost then cleared itself. Now the marker clears as soon as the player next to the piece is collision-checked,
    in practice the frame of the pickup. Regression test: `test_furniture.py ghost`.
- **2×2 draw offset:** the model sits on the shared corner (+0x1000 x/z), as in `ov004_furniture_object_init`.
- **Model cache** (heap object, at most 24 models; textures halved before upload, texture matrix enabled so UVs scale):
  - After a 30-frame settle delay, two texture arenas are claimed from the frame VRAM manager. Each leaves 0x200 free per region; in town that is about 43 KB.
  - One 12×0x80 palette block is claimed too.
  - Textures are sub-allocated first-fit inside the arenas (0x40 granule).
  - Eviction: least recently used among models drawn neither this frame nor the last; at most one load per frame. If everything is in view, a model more than 2 squares farther from the player gives way to a nearer one.
  - Uploads go through the game's own VBlank VRAM request queue (`vram_req_b_submit_texload`, the same path as the player's body textures). It flushes the data cache and copies inside the game's VBlank budget. The model shows as a leaf until its request is done, then the .nsbtx buffer is freed. A pending request is cancelled on eviction and teardown.
    - Before 2026-10-19 the draw loop uploaded directly, after a VCOUNT busy-wait, with no cache flush. A beach table placed outdoors froze a real DS (flashcart); melonDS doesn't model the cache or DMA timing, so it never reproduced there.
  - The heap's largest free block is checked first: at least 48 KB must be free before a load. This avoids the allocator's fatal path.
  - A refused model is not retried for 20 frames, so there are no per-frame cartridge reads.

- **Draw-loop cell:** the draw hook looks up the square's grid cell from the loop's position (`r7 + 0x9C`), the
  way the loop itself does. The pointer at `r7 + 0x90` reads the right item but isn't reliably that cell's
  address (seen +1 and +10 bytes off), and the leaf, lamp and coverage lists are keyed by cell. Found 2026-10-20
  while testing lamp switching.

## Limits / known behaviour
- **Texture memory is the ceiling.** Outdoor textures are loaded at half resolution (`tex_halve`, 4× less VRAM), so about 20+ distinct models show at once; 21 were drawn in the 24-piece stress test, at 20 fps. Beyond that, the farthest pieces show as leaves until the player walks closer. Details: `docs/OPTIMIZATION_REPORT.md`.
- Sitting and lamp switching are done (2026-10-20; lamp switching reworked 2026-10-22). Lying on beds, radios and other interactions are
  not. Research, effort and risk: `docs/research/outdoor_furniture_interaction.md`.
- Sitting in town is a simplified port: timed steps (20 logic frames) instead of the animation clock (it never
  reports "ended" for these animations in town), no sit sound, no sitting sideways on armless chairs, and the
  player is put back where they stood. Hardware check: the pose, and indoor sitting still working through the
  trampolines (not covered by the headless tests).
- Multiplayer: marker writes are local. Visitors see furniture as leaves unless they run the hack too.
- Vanilla save compatibility: a hacked town loaded in vanilla shows furniture as leaves. Any 0xF031 squares stay inert, special-id squares that can't be picked up.

## Evidence (screenshots in `build/screenshots/ftr_*`)
- `ftr_01_yard`: near pieces drawn in 3D, with the farthest falling back when the arenas are full.
- `ftr_10_collide_secondary`: the player stops at x=44.79 against the table's secondary square.
- `ftr_23_after_nudge`: the dropped classic bed (2×2) fills squares (10..11, 14..15) between two trees, with markers on 3 squares.
- `ftr_30_in_house` / `ftr_32_back_outside_settled`: on the house round trip `s_cache` goes to 0, is recreated at the same heap address (no leak), and the models redraw.
- `ftr_40` / `ftr_50`: B next to the marker of a 2-square table picks up the table (the anchor). B facing only a bed marker picks up nothing.
