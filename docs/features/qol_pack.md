# QOL pack: Bell bags, fruit stacks, Blathers, Nook's one-player sales

Status: **done on EU** (headless tests pass; not hardware-tested; US not mapped yet). Code: `src/heap/bells_pickup.c`,
`src/heap/fruit_stack.c`, `src/heap/museum_bulk.c`, patches in `tools/patches.py`, item records in
`tools/file_patches.py`. Tests: `tools/test_qol.py`.

Patches can now point at code-home functions: `build_rom.py` links the heap code before patching (the ITCM payload
has ~1 KB left, so new hooks live in the code home).

## Bell bags stack when picked up
- A picked-up Bell bag (ground pick-up, actions 0x19/0x1B, and shovel digs, ov003 action 0x60) is added to the first
  pocket bag it stacks with: 100 + 100 → a 200-Bell bag. It works with full pockets too (no "pockets are full" talk).
- Stacks only when the total is itself a bag: 100..900 or whole thousands up to 99,000. Otherwise (e.g. 900 + 1,000)
  the bag takes its own slot, as in vanilla. Wrapped or errand slots (pocket flags ≠ 0) are left alone.
- The wallet is never touched; moving the money into it stays the player's job (owner's choice, 2026-10-27).
- Hooks: the two calls of `player_action_19_pick_up_flow` (state 0, after the pick-up animation) and
  `pocket_put_item` in `ov003_player_action_60_end`.

## Fruit stacks up to 9
- Like Joan's turnip bundles, a stack is an item of its own: `0x156E + kind * 8 + (count - 2)` ("2 apples" ..
  "9 cherries", kind 0..4 = apple, orange, pear, peach, cherry). `tools/file_patches.py` writes the 40 records in
  the blank item_info space (0x56E..0x595) of every language: the fruit's record (icon, kind) with the price times
  the count, and plural names (English, French, German, Italian and Spanish). The 18 item_info accessors clamped
  any index >= 0x56E to "garbage"; their literal is 0x596 now.
- Picking up a fruit (or a dropped stack) while carrying the same kind adds it to that slot when the total is 9
  or less, with full pockets too (same hook as the Bell bags). Otherwise it takes a slot of its own.
- Eating a stack (Grab, then the player's portrait) eats one fruit; the rest goes back to the slot.
- Burying a stack in a hole ("Bury", or "Drop on Ground" facing a hole) plants one fruit tree; the rest stays.
- A stack is worth count x the fruit's value (`item_value`, town fruit and foreign fruit alike), so selling a stack
  to Nook pays the same as selling the fruit one by one.
- Dropping, mailing or giving a stack moves the whole stack. Mail, gifts and shops still hand out single fruit.
- Not handled: whatever asks for "a fruit" by the item id range (Wendell, villager errands) only takes single
  fruit, not a stack. Eat down to one, or keep a single fruit aside (9 + 1 does not stack).
- Hooks: `item_value`'s entry (jumps to `hook_item_value`, which runs the 4 moved instructions itself); the pockets
  screen's "held item dropped on the player" kind (3 calls of `func_ov096_0229ab98`), the two calls that start
  eating (`player_self_queue_action_85`), the held item after eating (`0x0229C65A`), the slot after eating
  (`0x0229C484`) or burying (ov098 `0x0229F198`); `item_to_field_obj_ids` in `func_02043d0c` (an item put in a
  hole). Probes: `tools/probes/fruit_eat_probe.py`, `fruit_bury_probe.py`, `item_value_probe.py` (the hook in play:
  a 1,000-Bell bag is worth 1,000).

## Several items for Blathers at once
- In Blathers' picker ("Donation!" and "Check a fossil!", menu code 0x21 = ov101), **X** marks the slot under the
  cursor, and X again unmarks it. A marked slot gets a green ring: the pocket grid's own mark (ov094 draws cell
  `0x02298648` on slots whose bit is set in the grid's mark bits, `+0xA40`), not a new graphic. **A** picks a slot as usual (a marked one too) and closes the picker.
- Blathers handles that item as in vanilla. Whenever he would open the picker again ("Sure is!" / "Yep!"), the next
  marked slot is handed to him instead. So the player answers his usual questions, but never goes back to the pockets.
- Items he already has are refused as in vanilla. A marked slot whose item changed since is skipped. Cancelling the
  picker, or a new conversation, drops the marks.
- Marking is d-pad only (X); picking by touch still works and takes the marks along.
- Hooks: ov101 sub-state 6 (member-pointer source at `0x0229A6A8`); ov047's choice handlers that open the picker
  (`0x0225EC38` donate, `0x0225EC20`/`0x0225EC28` assess), its after-picker handlers (`0x0225EC78`, `0x0225EC70`)
  and its talk step (vtable `0x0225ED48`, to drop marks at the greeting).

## Nook's sale day, evening sale and spotlight item with one resident
- `nook_daily_restock` (`0x020AE7F8`) skipped them unless the town had 2+ residents. `arm9 0x020AE8AA`: the
  `residents == 1 → skip` branch is a nop now. The other vanilla condition stays: some resident must have finished
  Nook's part-time job (player flag 1 is "job not finished"; Nook's end-of-job talk clears it).
- Evidence: `test_qol.py nook` forces a restock on load; with the patch the sale day's date gets written
  (Saturday 6 Jan in the test), vanilla writes nothing. `tools/probes/nook_restock_probe.py` breaks inside the
  restock and shows each check.
- Not tested in play: the evening-sale (1 in 14 days) and spotlight (1 in 5 days, not on sale days) rolls.

## US
None of the new addresses are in `tools/regions/adme.py` yet; run `tools/remap_region.py us` before a US build.
