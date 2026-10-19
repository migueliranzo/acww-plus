# Feature: shake trees with a fishing rod or net equipped

Status: **done** (verified headless; `tools/test_tree_shake.py`, rod + net PASS).

## Behaviour
- **Rod in hand:** A facing a tree shakes it (actions 0x68 → 0x69), the same as with empty hands. With no tree ahead, A casts as usual.
- **Net in hand:** A facing a tree shakes it, unless a bug is within about 2.5 units of the player (one on the trunk, or bees that just came out). Then the net swings as usual, so tree bugs can still be caught.
- The tool stays in hand.

## How it works (`src/tree_shake.c`)
- `func_ov003_022085dc` (the A-button "use" handler) calls `func_ov003_02208430(player, tool_kind, target)` from 8 places.
- The dispatcher shakes trees only for kinds 0 (empty) and 10 (umbrella or toy). Kind 3 (rod) casts and kind 4 (net) swings.
- All 8 BLs go to `hook_ov003_use_dispatch`. For kinds 3/4, it first runs the dispatcher's own kind-0 branch on a copy of the target:
  - reach `< 0x2334`
  - `func_0200f9cc(player, pos, 1, 0)` creates the field shake job only for a shakeable square
  - `func_ov003_0220bb94` queues action 0x68
  - If that returns 0, the original kind runs.
- Bugs near the player come from ov003 list A: `0x0225DD4C`, 8 slots of 0x25C bytes; +0x24D id (−1 = empty), +0x204 position.

## Not verified
- The test save is in January (no bugs), so the "bug nearby → net swings" path was not exercised in the emulator.
- The shake animation was run with a tool in hand (actions observed), but the camera angle in the test hides the player behind the tree, so it was not inspected visually.
