# Feature: change skin tone on the bedroom (attic) phone

Status: **done** (verified headless; `tools/test_skin_tone.py` 2/2 PASS, face colour measured: 246→225→215→199→214 for Darker ×3, Lighter).

## Player view
- Upstairs phone → Service Center → new entry **"Skin tone."**:
  - on the wake-up screen: Reset clock / Set sound / Skin tone / Downloads / Nothing
  - after walking upstairs: Set sound / Skin tone / Downloads / Nothing
- "What kind of skin tone would you like?" offers **Lighter / Darker / This is fine**.
  - Lighter and Darker step the tone (8 tones, 0–7). The player model updates immediately: "There we go! How does that look?"
  - The question then comes back. "This is fine." returns to "Is there anything else I can do for you?".
- The chosen tone is permanent. Summer tanning still darkens the player, and the tan fades back to the chosen tone instead of to the palest one.
- Text is English in all five languages (fallback until translated).

## How it works (`src/skin_tone.c`, text in `tools/file_patches.py`)
- Skin tone = tan level (player record +0x223D bits 3–5). Skin palette = `PPal[8 × face + tan]` (`player_palette_ids`).
- **Saved base tone:** PostOffice `pad_98e` (save block `0x14FCA`, RAM `0x021EF9C2`), never written by the game.
  - 4 bits per player, holding base + 1. 0 means not set, so vanilla saves behave exactly as before.
- **Menus:**
  - ov004 choice-list literals `0x0222D5EC` / `0x0222D5F0` and next-message table literals `0x0222D4A8` / `0x0222D4AC` point to tables in the payload.
  - The cancel indices at `0x0222D5A6` / `0x0222D5B2` go 3→4 and 2→3.
- **New text:** select2 #22 "Skin tone."; sequence1_ messages 0x43 (question, inline choice `{2:1:44451f}`) and 0x44 / 0x45 (reply, continues to 0x43).
- **Tone step:** the phone talk's message-open callback (`func_ov004_0222d544`) is replaced by `hook_phone_msg_open`.
  - It is registered from the literal at `0x0222D9D8`; the vtable copy at `0x02251A04` is patched too.
  - Opening 0x45 / 0x46 steps the tone, writes the tan and the base, re-requests the head build (`func_0200fb8c`) and refreshes the body palettes + upload (`body_colors_refresh`).
- **Wake-up screen:** no player is current yet, so the code uses the sleeping player's actor (actor table `0x021D3F04`) and `player_record(actor)`.
- **Fading floor:** both calls of `player_tan_level` (`0x0200DF00`, `0x0200FC6E`) go through `hook_player_tan_level`, which never returns a value below the base and stores it when the caller writes.

## Tools added
- `tools/bmg_tool.py`: BMG read, modify and write, with an LZ10 / 0xF7-chunked compressor. It rebuilds all 40 select and sp/etc BMGs byte-identically after decompression.
- `tools/file_patches.py`: NitroFS edits applied by the build. Edited files are restored from vanilla on the next build.

## Not verified / notes
- The walked-upstairs menu variant (scene ≠ 6) was not driven in the emulator. Only the wake-up screen was.
- Fading over real days was not simulated. The floor logic is a direct clamp in the hook.
- On the wake-up screen, the head rebuild resets the face animation, so the sleeping player's eyes open. This is cosmetic.
