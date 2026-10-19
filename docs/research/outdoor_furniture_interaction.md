# Research: sitting on outdoor furniture, interactive / glowing lamps

Status: research only (2026-10-20), nothing implemented. Rotation, animations and storage are out of scope.
Sources: `N3\ov004_classes.json`, `N3\work\h00.md`–`h02.md` (ov004 furniture classes), `N2\action_table.json`.

## How the game does it indoors
- Every placed indoor piece is an ov004 **actor** built on the furniture base class (`0220d148` ctor, ~0x840 bytes per
  actor). The kind table `0x02244000[kind]` picks the class: chairs/sofas are profile **0x36**, beds 0x37, lamp **0x3F**,
  radios 0x3A.
- **Sitting:** the chair class's update watches the player push into a seat side (touch record `02238b5c`, side 0/1/3)
  and calls `02228120`, the sit request. That queues player actions **0x25–0x2C** (sit down front/L/R, sit wait,
  turn L/R, stand up). All eight action handlers live in **ov004** (`0x022246F8..0x02225500`, about 3.5 KB of Thumb code),
  and they use ov004 helpers for seat positions and the piece actor.
- **Lamps:** class 0x3F is an on/off piece: A toggles a pair at +0x73C, `state_flag` says "is on", and the model's
  material animation shows the lit shade. Room light comes from `ov004_count_lit_pieces` feeding the indoor lighting
  setup. The DS has only 4 directional hardware lights, so no piece lights its surroundings; a lamp only changes its
  own look and the room's global light level.

## Why it doesn't carry over outdoors
- ov003 (town) and ov004 (indoors) share one overlay slot, so none of the actor classes, sit actions or helpers are
  in memory outside. The player action table entries 0x25–0x2C point into ov004 addresses that hold ov003 code in town.
- Outdoor furniture is not an actor at all: our hook draws the model from the item grid and gives it a collision
  cylinder. Nothing in town has per-piece state.

## Options, effort and risk
| Feature | What it takes | Code | Effort | Risk |
|---|---|---|---|---|
| **Lamps glow at night** (no interaction) | In the draw hook, for lamp-kind models, raise the material emission after dark (the time-of-day light is already read there). | ~150–250 B | small (one session) | low |
| **Lamp on/off with A** | Hook the town A-press check for the square in front, keep the on/off state somewhere (RAM list of squares, or reset per visit), switch emission or the material animation. | ~0.5–0.8 KB | medium | medium (A-press path also handles signs, villagers, items) |
| **Sit on chairs / sofas / benches** | Port the eight sit actions (0x25–0x2C) plus the seat-side detection, rewrite their ov004 helper calls, redirect those action ids to our code while ov003 is loaded, place the player on the drum-bent ground at seat height, and get up cleanly when a scene change, a villager talk or a save interrupts. Beds (lie down, 0x08–0x0F) would be a second port of similar size. | ~4–6 KB | large (several sessions, a lot of emulator plus hardware testing) | high: player state machine, multiplayer sync of actions, saving while seated |

## Code space
- The ITCM payload has **524 bytes** left (after the 2026-10-20 ghost fix and tree-drop leaves). Lamp glow just fits; on/off
  does not fit; sitting clearly needs a new code home.
- Most realistic new home: a **code file loaded into a root-heap block at boot** (NitroFS file + a small loader in
  the ITCM payload; position-independent or linked at the allocated address with a fixed heap reservation). It
  costs ~5 KB of heap for the session. The empty overlays (ov000, ov057–064, ov089) could carry the file, but they
  still need a free RAM range to load into, and none is known. ov003's 0x238-byte tail slack is too small.
- Measuring DTCM stack use (16 KB, 1120 B of data) could free a few KB, but stack overflow there would crash hard,
  so it needs worst-case measurements first.

## Recommendation
1. Lamp glow at night: cheap and safe, worth doing if wanted.
2. Lamp on/off: only after the new code home exists.
3. Sitting: build the code home first, then port the chair sit actions as a separate project. Beds after that.
