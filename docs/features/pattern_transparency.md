# Feature: patterns can use transparency

Status: **done**. Rendering is verified headless (`tools/test_pattern_alpha.py`: vanilla draws index-0 pixels black, AC:WW+ shows the ground through). The editor input change is code-level only (see below).

## Player view
- In the design editor, **L / R now cycle through a 16th colour: transparent** (… 14, 15, transparent, 1 …).
  - With transparent selected, no colour cell is highlighted.
  - Painted pixels show as see-through on the canvas.
  - The eyedropper (B) picks transparent from such a pixel, as in vanilla.
- Transparent pixels are see-through wherever the design is drawn as its own texture:
  - designs laid on the ground (the ground or path below shows)
  - umbrellas (see-through spots)
- On worn shirts and hats the design is composited into the body texture, so transparent pixels stay opaque there (the palette's colour 0, black). This is unchanged from vanilla.

## How it works
- Design pixels are 4bpp indices into one of 16 fixed palettes (`/menu/desi/b_myd_ten0_obj.bpl`).
  - Index 0 is 0x0000 in all of them. Vanilla never uses it: the editor offers 1–15, and no ROM design contains it.
  - So existing designs are unaffected.
- **Texture:** `design_textures_build` uploads each of the 32 player design textures with `tex_vram_alloc_load`; the call at `0x02071864` goes to `hook_design_tex_upload` (`src/pattern_alpha.c`).
  - The hook sets TEXIMAGE bit 29 (colour 0 transparent) in the TEX0 texture entry first.
  - `texcache_get` then copies that header into the table `0x021CF428` that the ground drawing binds.
  - After an edit, `player_design_texture_refresh` re-uploads only texels and palette into the cached texture, whose param keeps the bit.
- **Editor (ov123):** `func_ov123_02295e40` handles L/R.
  - `0x02295E58`: `cmp r1,#1` → `#0` (L: 1 → 0 → 15)
  - `0x02295E90`: `mov r1,#1` → `#0` (R: 15 → 0 → 1)
  - The colour setter puts the highlight at (c − 1) × 12 + 0x80, which is off-screen for c = 0.

## Not verified
- The editor (reached from the Able Sisters) was not driven in the emulator. The L/R change is two constants in a function whose disassembly matches the decomp.
- Umbrella rendering with transparency was not looked at.
- The Able Sisters' displayed designs and villagers' shirts use other textures and stay opaque.
