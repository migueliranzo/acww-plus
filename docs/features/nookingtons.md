# Feature: Nookington's without multiplayer

Status: **done** (code patch; the owner tests it in play).

## Vanilla rule
- `shop_next_stage` (`0x020AECDC`) upgrades the store one level when `sales >= shop_sales_needed(level)`.
  - The needs are 25,000 / 90,000 / 240,000 Bells.
- From level 2 (Nookway) to 3 (Nookington's) it also needs `shop_visitor_sale_flag_test` (`0x020AEA8C`) to return true.
  - That function tests bit 7 of the town flag word (block `+0x15FD8`).
  - The bit is set only when a buyer from another town buys something (`func_020aea9c`).
- `shop_remodel_schedule` (after each purchase) and `shop_remodel_end` (daily update at 06:00) both go through `shop_next_stage`.
  - So without the flag, the remodel is never scheduled.

## Patch
- `arm9 0x020AEA8C`: `01 48 07 21` → `01 20 70 47` (`movs r0,#1; bx lr`).
- The function's only reference is `shop_next_stage` (checked in the main-module decomp).
- The flag bit itself is untouched, so nothing else changes.

## Expected in play
- With Nookway and 240,000 Bells of sales, the next purchase schedules the remodel (Nook's notice).
- Nookington's opens two days later, as for the earlier upgrades.
- A save that already reached the cap at level 2 upgrades after its next purchase.
