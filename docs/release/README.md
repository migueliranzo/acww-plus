# AC:WW+ (alpha)

A quality-of-life hack for **Animal Crossing: Wild World (Europe)** that keeps the game's feel. This is an
**alpha**: tested on an emulator and on a real DS with a flashcart, but not by many people yet. Back up your save
before you start.

## Features
- **Furniture outdoors.** Drop furniture from your pockets and it stands in town as its real 3D model, facing the
  way you faced. It is solid, and big pieces (benches, tables, beds) block all their squares. Pick it up with B as
  usual. Furniture shaken out of trees still lands as a leaf.
  - About 20 different models show in 3D at once; beyond that, the farthest pieces show as leaves until you walk
    closer.
- **Transparent patterns.** In the pattern editor, L/R cycles past colour 15 to "transparent". Transparent pixels
  of a design laid on the ground show the ground through. (On clothes they stay black, as before.)
- **Skin tone.** The upstairs phone's Service Center has a new "Change my look." entry: pick a lighter or darker
  base skin tone. Summer tanning still works and fades back to your chosen tone.
- **Shoe and sock colours.** Same menu: cycle through shoe and sock colours.
- **Shake trees with a net or rod equipped.** A at a tree shakes it. With the net, a bug close by is still caught
  instead.
- **Tools with L / R.** Tap R to swap to the next tool in your pockets, L to put it away or take it back out.
- **The monkeys** (Champ, Nana, Simon, Tammi, Monty, Elise) can move into your town.
- **Nookington's** without multiplayer: the shop's last upgrade no longer needs a visitor's purchase.

New text is in English in every language for now.

## How to patch
1. You need your own dump of *Animal Crossing - Wild World (Europe) (En,Fr,De,Es,It)*, game code ADMP,
   CRC32 **C677970C** (other hashes in `hashes.txt`). For the US version use `acww_plus_<version>_us.bps` (first
   release) or `acww_plus_<version>_us_rev1.bps` (revision 1). The Japanese version won't work.
2. Open [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) (or Flips), choose your ROM and the `.bps`
   file, and apply. A wrong base ROM is refused.
3. Play the patched ROM on a flashcart or an emulator.

## Saves
- **Flashcarts and emulators:** name the save like the patched ROM (`acww_plus.sav` next to `acww_plus.nds`). Wild World saves are 256 KB; some flashcarts (the original R4 and many clones) want 512 KB and call a 256 KB save "damaged". Resize it with https://savefileconverter.com/#/flash-carts. More in the main README: https://github.com/migueliranzo/acww-plus#using-your-save-on-a-flashcart-or-an-emulator
- Your existing EU save works as is.
- Going back to the original game: the save loads, and the hack's extras are ignored:
  - Shoes and socks are back to their normal colours.
  - Your skin tone starts fading back the original way.
  - Transparent pattern pixels show as black.
  - Outdoor furniture shows as leaves.
- **Before going back, pick up any 2-square or 4-square furniture you placed outdoors** (benches, tables, beds).
  Their extra squares hold a marker the original game can't clear: you couldn't drop anything on those squares.

## Known limits
- Local multiplayer: visitors who don't run the hack see your outdoor furniture as leaves.
- If you see a freeze or crash, please report what you were doing, the furniture outdoors nearby, and whether it
  was a flashcart or an emulator (which one).

## About this release
A personal project, shared as is: I may fix bugs, but I'm not planning further development. Everything is open
source, so anyone can take it further.
Source, issues and updates: https://github.com/migueliranzo/acww-plus
