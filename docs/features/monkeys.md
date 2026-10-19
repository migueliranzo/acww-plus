# Feature: the monkeys can be obtained in regular play

Status: **done** (data patch; the owner tests it in play).

## Vanilla rule
- The species table is at `0x020CC9B8` (150 records × 0x4E). Byte +0x4B is the move class:
  - 0 = may be a starting resident or move in
  - 1 = move-in only
  - 2 = never chosen
- `villager_pick_species` takes class < 2 for move-ins and class 0 for a new town's three residents.
- Champ, Nana, Simon, Tammi, Monty and Elise (species 0x90–0x95) are the only class-2 species.

## Patch
- One byte per monkey: class 2 → 0, at `0x020CF5E3`, `…631`, `…67F`, `…6CD`, `…71B`, `…769`.
- They join both pools:
  - starting villagers (new town)
  - natural move-ins, chosen by the usual least-common-personality draw (jock, normal, lazy, peppy, cranky, snooty respectively)
- Assets are present in the ROM:
  - `npc/model/144/144..149.nsbmd` / `.nsbtx`
  - catchphrases and house furniture lists in the species data (`u4b/villagers.json`)

## Notes
- The past-resident reset (`villager_past_set_reset`: "every class < 2 species has lived here") now also waits for the monkeys. That is harmless.
- Existing towns keep their residents. The monkeys show up as move-ins when a plot frees up.
