# Research: item groups per town, and Nook's "2 or more players" features

Status: research (2026-10-25). **Update 2026-10-27:** the 2-resident rule is patched out (one resident is enough;
see `docs/features/qol_pack.md`). Player flag 1 turned out to be "Nook's part-time job not finished", so a one-player
town gets the sale day, evening sale and spotlight item once the job is done. Prompted by a community comment:

> The game divides furniture and clothes into groups (A, B, C, D) which are different per town. One of those groups
> has a 0% (I think) chance, to encourage trading via multiplayer. [...] Nook's Spotlight Special and Point Sales are
> only unlocked after having at least 2 player characters in town.

Sources: the reference decomp (`func_*` names below), the vendor/Nook notes `RUNS\2026-10-15-u0\u4a\frag\nook.md` and
`vendors.md` (their generators reproduce every saved shop stock from 49 play sessions), and `nook_pools.json`
(item lists per group). EU addresses.

## Short answer
| Claim | Verdict |
|---|---|
| Furniture and clothes are split into groups that differ per town | **True.** Three groups (the wiki's A/B/C), weighted per town. |
| One group has a 0% chance | **False for the normal groups.** Each town gets 60% / 30% / 10%, so the town's weakest group still shows up, just rarely (10%). |
| A fourth group ("D") | **Exists:** a 43-item "rare" group. In a one-player town, Nook never stocks it, but it isn't 0% overall: shooting-star wishes give it. |
| Spotlight item and Nook's sales need 2+ characters | **True.** The rare "spotlight" item, the evening half-price sale and the sale day all sit behind a "2 or more residents" check. |

## 1. Item groups

### How the game assigns them
- Every furniture model has a **class** (byte 4 of its `ftr_info/always.bin` record; clothes and other items have the
  same idea in `item_info`). Nook's and Able's daily stock only ever picks from a few "shop" classes.
- Each town has a 9-byte **town code** (save block `0x15FBC`, set when the town is created). Byte 0 picks the
  furniture weighting, byte 1 stationery, byte 2 shirts, byte 3 carpets, byte 4 wallpaper.
- `item_pool_class_draw` (`0x020638F8`) uses that byte (mod 6) to choose one of six orderings of
  **[60, 30, 10]** (table `0x020CBBDC`), so every town has one 60% group, one 30% group and one 10% group, in its own
  order. Example from the test town: furniture groups 1/2/3 = 30% / 60% / 10%.
- Feng shui (the colour-matching in your house) can shift those odds a bit. With normal houses (score under 5) the
  split is exactly 60/30/10.

### The groups
| Group (class) | Items | Where it appears |
|---|---|---|
| Furniture 1 / 2 / 3 (the wiki's A/B/C) | 121 / 122 / 122 | Nook's daily furniture slots, villager gifts and other random gifts, weighted 60/30/10 for your town |
| Furniture 4, "rare" | 43 | see below |
| Shirts 1 / 2 / 3 | about 81 / 82 / 82 | Able Sisters, same 60/30/10 scheme on town-code byte 2 |
| Stationery, carpets, wallpaper 1 / 2 / 3 | 16–19 each | Nook, same scheme |

So the "trade with other towns" encouragement is real, but softer than the comment says: your 10% group is
uncommon, not missing. Per day Nook stocks 2–8 furniture slots (by store stage), each slot a 10% chance of being
from your rare group. You will see those items, just slowly.

### The fourth group: rare furniture (class 4)
43 items: the moon, the chess kings and queens, the throne, the treasure chest, the Master Sword, the Arwing, the
lucky gold cat, the samurai suit, the ninja sword, the jukebox, the ivory piano, the hi-fi stereo, the dolly, the
hamster cage, the skeleton, the mummy's casket, and more (full list in `nook_pools.json`, class `0x04`).

Two code paths ask for this group:
1. **Nook's spotlight item:** at the daily restock, 1 day in 5 the first furniture slot is replaced by a rare item
   and Nook announces it. This is behind the 2-player check (section 2), so **a one-player town never gets it from
   Nook.**
2. **Shooting stars:** when a player wishes on a shooting star (outdoor player action `0x72`, the `pray1` animation,
   in ov003), the game sets player flag `0x32` (`func_020B92C4`). The next time letters are handed out,
   `players_flag32_gift_letter` (`0x020BCE70`) sends that player a letter with a random **rare** item and clears the
   flag. **This works with one player**, so rare items are not 0% in single player, just limited to one per wish.

Not checked yet: the villager gift tables (they pass `{pool, class}` records from data tables), the lottery and
other event prizes. Some of them may also draw the rare group.

### On "a whole fourth of the catalogue"
The three normal groups together are 365 of the 1,769 furniture models; the rare group is 43 (2.4%). Most furniture
comes from elsewhere anyway (events, fish/bug models, gyroids, fossils, paintings, Redd's own groups `0x26`/`0x27`,
Gracie, etc.). In a one-player town, the only part of the shop catalogue that is noticeably harder to get is the
rare group, and that is through Nook only.

## 2. Nook's features that need 2+ players

At each daily restock (`nook_daily_restock`, `0x020AE7F8`), after the normal stock is generated:
```
if residents >= 2 (func_02097BF0 counts used player slots in the save)
   and some resident has player flag 1 clear (meaning not decoded yet):
    sale-day scheduling        (nook_sale_day_update)
    1 in 14 days: an evening sale from 17:00-20:00 (prices halved), announced
    otherwise, unless today is the sale day:
        1 in 5 days: first furniture slot = a rare-group item (the "spotlight"), announced
```
- **"Residents"** means player characters saved in this town (up to 4), not visiting friends.
- With one character, none of the three ever happens. This was confirmed against real play sessions: one-player
  sessions whose dice would have rolled an evening sale show none.
- What each one is, in player terms:
  - **Spotlight item:** a rare (class 4) piece in the first furniture slot, with an announcement.
  - **Evening sale:** all prices at half from the announced hour until 22:00.
  - **Sale day:** a weekend day (Saturday or Sunday) scheduled ahead and announced 4 days before; purchases that
    day earn 5× Nook points.
  - Which of these the community calls "Point Sales" is my best guess: probably the sale day (5× points).

## 3. What changing them would take (not done; for a later decision)
| Change | How | Effort | Risk / feel |
|---|---|---|---|
| Spotlight item and Nook's sales with 1 character | Change the `>= 2` test in `nook_daily_restock` to `>= 1` (a 1–2 instruction patch, like the Nookington's change). Check what player flag 1 is first, so the second condition doesn't block one-player towns anyway. | small | low. It only turns on vanilla features the game already has. Fits the hack's "Nookington's without multiplayer" spirit. |
| Weaker town groups (for example 40/30/30) | Edit the 6×3 weight table at `0x020CBBDC`. One data patch affects Nook, Able, villager gifts and everything else that uses the groups. | small | medium for the game's feel: towns become less distinct, and trading matters less. A gentler option is only raising the 10% share. |
| Rare items from Nook in one-player towns | Comes free with the first row. | – | – |

Open questions before any change:
1. Player flag 1: what sets it? If it marks "the town's first player" or similar, the condition would need a look.
2. The villager gift tables: which groups they use (they may already give rare items in single player).
3. Whether the US version has the same thresholds (it should: same code, remapped addresses).
