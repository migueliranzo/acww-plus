# Feature: shoe and sock colour variations

Status: **done** (verified headless; `tools/test_skin_tone.py` look-byte PASS, and `tools/probes/look_town.py`: red shoes and green socks render on the boy and the girl).

## Player view
- Upstairs phone → Service Center → **"Change my look."** → Skin tone / **Shoes** / **Socks** / That's all.
  - Shoes and Socks step to the next colour each time ("How about these shoes?"), then the menu returns.
  - After the last preset the model's own colours come back.
- Shoes: own, red, black, brown, white, green, yellow, pink, purple, navy, orange, blue.
- Socks: own (white), black, grey, red, navy, pink, yellow, green, brown, purple, sky blue.
- Choices are per player and saved.

## Where the colours are (mapped in the emulator)
- Shoes and socks are part of the body models' own palette `b1_pl` (`PBody/boy|grl.nsbmd`), not of the clothes.
  - **Boy:** shoes = indices 7–11 (a ramp from the colour to near white), socks = 4 (the vanilla green, (0, 160, 80)).
  - **Girl:** shoes = 1 (colour) and 3 (lighter), socks = 0 (black) and 4 (navy edge).
  - The socks are the band between the shirt and the shoes. They are hard to see while walking and clear with the player in bed (wake-up screen, phone menu).
    - Mapped on the wake-up screen with marker colours. Those entries are used only by that band of texture `b1`.
    - An earlier version recoloured the white entries (boy 12–15, girl 14–15). Those are the shoe's white trim, not socks (owner report, 2026-10-19).
- Found by painting index groups in debug builds (`BODY_COLORS_DEBUG` 1/2/3 in `src/body_colors.c`) and zooming on the player's feet.
- Probes: `tools/probes/body_map2.py`, `tools/probes/body_map_girl.py`. Analysis tool: `tools/analysis/nitro_tex.py` (TEX0 lister and renderer).

## How it works (`src/body_colors.c`)
- Every player body is a per-player RAM copy (`player_body_cache`) with its own VRAM slot.
  - `hook_player_body_loader` (BL at `0x0200DF10`, actor init) recolours `b1_pl` in that copy before the first upload.
- **Saved choice:** PlayerTasks padding, player record **+0x1DD9**: low nibble shoes, high nibble socks. 0 = the model's own colours, so vanilla saves look the same.
- **Live change from the phone:** `body_colors_refresh` does four things:
  - restores the model's shoe and sock colours
  - applies the choice
  - re-reads the skin palettes (`player_palette_ids`) and copies `skin_pl` into the body texture
  - queues the body texture upload through the game's VBlank queue (`vram_req_b_submit_texload`)
- The skin tone change uses the same refresh, so arms and legs follow the new tone too.
- `skin_tone.c` handles the menu (messages 0x43–0x48, see `skin_tone.md`).

## Not verified
- The live recolour while on the phone: the player is in bed on the wake-up screen, so the feet are hidden. It ran six times in the test without problems. The saved colours render after waking (verified).
