# Feature: swap or put away tools with L / R

Status: **done** (verified headless; `tools/test_tool_swap.py`, 7/7 PASS).

## Controls
- **R** (tap, standing): equip the next tool from the pockets. The tool in hand goes into the slot the new tool came from, so repeated taps cycle through every tool (shovel → net → rod → shovel …).
- **L** (tap, standing): put the tool in hand away into the first free pocket slot. With empty hands, L takes the last put-away tool back out (or the first tool in the pockets).
- Holding L/R while walking still runs, as in vanilla. Only a tap with no direction or face button held counts.
- A tap made during the equip animation is buffered (about 20 game frames).
- Nothing happens while a menu is open, during events or conversations, or whenever the hub would refuse to open the pockets.
- Tools are items 0x1369–0x137B: shovel, axe (all wear states), rod, net, watering can, slingshot, and the golden versions.
  - Umbrellas are not cycled.
  - Held toys (0x13A0–0x13A7) are never put away; vanilla destroys them when unequipped.
- If the pockets are full, L keeps the tool in hand.

## How it works (`src/tool_swap.c`)
| Hook | Where | What |
|---|---|---|
| stand tick | rodata pair `0x020D65A4` (action 2), copied into the action tick table by `func_02005368` | buffered tap → swap, if the field is free |
| action 5 tick | pair `0x020D6804` | after an L/R equip, `player_request_stand(actor, 3, 5, -1)` |
| action 0x3F tick | pair `0x020D6634` | buffers taps during the equip animation |

- **Equipping:** `func_02094ec4(&item)` queues player action 0x3F, the same request the pockets screen's doll uses. The game's priority rules decide whether it is accepted; the pockets are only written when it is.
- Action 0x3F ends in action 5 (the "item selected" pose the pockets screen holds until it closes). From the field nothing closes it, hence the action-5 hook.
- **Field-free test:** the same conditions `menu_manager_tick` uses before Y opens the pockets:
  - control byte `0x021C70A0 == 2`
  - `menu_is_idle()`
  - `0x021DA914 == 0`
  - `!event_current_exists()`
- **Pad:** the game's own pressed/held words (`0x021F7E82` / `0x021F7E80`).

## Notes
- Taps shorter than about 3 vblanks can fall between pad samples in the emulator. Real presses are longer.
- Taps are also captured during the walk (action 3, pair `0x020D6814`) and skid (action 4, pair `0x020D680C`) ticks, while no direction is held. A tap made while slowing to a stop counts once the player stands.
