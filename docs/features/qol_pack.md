# QOL pack: Bell bags, Blathers, Nook's one-player sales

Status: **done on EU** (headless tests pass; not hardware-tested; US not mapped yet). Code: `src/heap/bells_pickup.c`,
`src/heap/museum_bulk.c`, patches in `tools/patches.py`. Tests: `tools/test_qol.py`.

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

## Several items for Blathers at once
- In Blathers' picker ("Donation!" and "Check a fossil!", menu code 0x21 = ov101), **X** marks the slot under the
  cursor, and X again unmarks it. A marked slot is greyed with the picker's own grey-out (the same look as items he
  won't take). **A** picks a slot as usual (a marked one too) and closes the picker.
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
