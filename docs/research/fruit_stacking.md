# Research: fruit stacking that fits the game

Status: research only (2026-10-27), nothing changed. EU addresses.

## How fruit works now
- Fruit is 5 items, `item_is_fruit` (`0x0204C184`): 0x1518 apple, 0x1519 orange, 0x151A pear, 0x151B peach,
  0x151C cherry. Each takes one of the 15 pocket slots (player +0x1B22, u16 each).
- The value comes from `item_value` (`0x0204BF98`): record price / 5 for the town's own fruit (100 Bells), the full
  record price for foreign fruit (500).
- Code that tests the fruit range (each would need to know about stacks):
  - `func_02043D50`: burying fruit plants a fruit tree;
  - `func_0204509C`: tree / fruit item mapping (table `0x020C9750`);
  - `acre_stats_scan`, `func_02049F68`: fruit lying on the map;
  - `ov096_held_equip_kind` (pockets screen): fruit can be eaten;
  - Wendell (`ov079_wendell_give_design`, `func_ov079_022758F4`): he asks for fruit;
  - `villager_letter_answer`, `func_02096284`, `weather_ctor`, the signpost message: smaller uses.

## The game's own "stack": turnips
WW already sells turnips as stacks that are separate items: 0x1531 "10 turnips" … 0x153A "100 turnips" (records
priced 10..100, one icon 0x1F, names in `item_info/<lang>/dma.bin`). Joan hands out as many stack items as needed.
A fruit stack made the same way would look and behave like something the game already has.

## Room for new items
- `item_info/<lang>/always.bin` (12 B) and `dma.bin` (20 B, name at +3) both have **0x600** records; only 0x56E
  are used. **0x156E..0x15FF (146 ids) are blank in every language.**
- But every item_info accessor clamps an index ≥ 0x56E to 0x56D ("garbage"). There are about 26 of these clamp
  sites (literal 0x56D) in `0x02061B10..0x02062310`. Using new ids means raising each clamp (data-only patches, but
  every one has to be found).

## Options
| Option | What the player sees | Work | Fit |
|---|---|---|---|
| A. Fruit stack items, turnip style (**recommended**) | Picking up a fruit while carrying the same kind adds it to that slot: "apple" → "2 apples" … up to "9 apples" (shown in the item name, fruit icon). Nook buys a stack for n × the fruit price. | Medium-large: 40 new records (5 fruits × 2..9) in 5 languages, the clamp patches, a merge hook on pick-up (the Bell-bag hook already sits there), `item_value` for the new range, and splitting (below). | Good: same idea as turnips; no new screen. |
| B. A hidden count per pocket slot | Same as A, but the count lives outside the item id. | Large: the pocket slot flags have only 2 bits per slot (value 3 unused, bits 30-31 unused); a count needs new save space and every pocket copy (menus snapshot the pocket at `0x021CEBF0`) would have to carry it. | Poor: invisible state, fragile. |
| C. Bigger pockets | – | Very large (every pocket screen and the save). | Poor. |

## What option A needs to handle
1. **Merge:** ground pick-up (`player_action_19_pick_up_flow`, already hooked for Bell bags), shovel digs (hooked),
   and fruit shaken from trees (lands on the ground, then the same pick-up). Mail, villager gifts and shops would
   still hand out single fruit.
2. **Splitting, so a single fruit is still easy to get:**
   - eating a stack (pockets screen, `ov096_held_equip_kind`) eats one, n-1 stay;
   - burying a stack (planting) plants one fruit tree, n-1 stay in the pocket;
   - Wendell and errands ask for one fruit: give one, keep the rest.
   The simplest rule that covers every other case: dropping a stack on the ground drops the whole stack; picking it
   up again merges it back.
3. **Value:** `item_value`: stack of n = n × single value (native 100, foreign 500).
4. **Names:** "2 apples" … "9 apples" in each language's dma.bin, written the way the turnip names are. New text is
   English-only today (see PROGRESS.md), so the four other languages need translations or English fallbacks.
5. **Ground drawing:** a dropped stack is drawn with its record's icon (the fruit's), same as one fruit.

## Open points before building
- Maximum stack: 9 (later games) or 10 (turnip-like round numbers).
- Native vs foreign is not a problem: it depends only on the kind (apple is native in an apple town), so all
  fruit of one kind has the same value in a given town.
- Find all 26 clamp sites and check nothing else indexes item_info directly (catalog, ov094 sprites via record +2).
