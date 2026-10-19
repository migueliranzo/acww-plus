# Performance and hardware deep dive (2026-10-19)

Question from the owner: can more than ~5 outdoor furniture pieces be rendered? What are the real limits of the DS here? Could DSi mode help (more memory, faster CPU)?

Everything below was measured headless on ndsref (melonDS-based) unless marked as research. Probes live in `tools/probes/`.

## 1. Where the limits actually are (town, vanilla)

| Resource | Town usage | DS limit | Verdict |
|---|---|---|---|
| Texture VRAM | banks A, B, C = 384 KB, all taken by the scene; ~48 KB left in two frame-VRAM regions after load | 384 KB of texture slots in this configuration | **The bottleneck** for furniture |
| Texture palette VRAM | bank E (64 KB), ~15 KB free | 64 KB (+F/G) | Plenty |
| VRAM D (128 KB) | assigned to ARM7 (MST=2); holds 106 KB of ARM7 code (the wireless driver), unchanged over time | n/a | **Not reusable**: banks are mapped whole, and the ARM7 runs from it |
| Polygons / vertices per frame | 358 / 885 (vanilla, walking south); 821 / 1,864 with 21 furniture models | 2,048 / 6,144 | Large headroom |
| ARM9 time | 41% busy (59% idle in `OS_Halt`) per 3-vblank frame | — | Large headroom |
| Frame rate | 20 fps in town **and** in the house (84% idle indoors) | — | A fixed design cap (game logic ticks at 20 Hz), not a load limit |

(VRAMCNT read through the emulator: A/B/C MST3 = texture slots 0–2, D MST2 = ARM7, E MST3 = texture palette, F/G = BG/OBJ A, H/I = BG/OBJ B. `tools/probes/budget_probe.py`, `vramd_probe.py`, `house_fps.py`.)

## 2. Findings and fixes

### 2.1 Cache thrash bug (fixed)
- With 10 distinct pieces in view, town fell from **20 to ~8 fps**: about 165 model loads and evictions per 300 vblanks, roughly 4 reloads per game frame.
- **Cause:** a model counted as evictable when "not drawn this frame", which also matches models the draw loop simply has not reached yet.
- **Fix:**
  - evict only models drawn neither this frame nor the last
  - at most one load per frame
- **Result:** 100/100 game frames per 300 vblanks, with 0 reloads at rest (`perf_probe.py`, `fps_probe.py`).

### 2.2 Half-resolution outdoor textures (new): 5 → 21 models at once
- Furniture textures are mostly 64×64 4bpp; the median model needs 3 KB and the worst 8 KB.
- `tex_halve` (`src/outdoor_furniture.c`) does the following before upload:
  - 2× nearest-neighbour downsample of every texture, in place, with the texel data packed
  - writes the halved size into the TEX0 dictionary and its `extraParam` (original width and height)
- After binding, NitroSystem computes `magW` / `magH` = 0.5 but applies them only through the texture matrix. So affected materials get `TEXMTX_USE` and texgen = texcoord.
  - Without that, repeating textures tile 2×, and clamped ones (the exotic lamp) smear their edge texels. This was checked by reading the bound material state from RAM (`mat_probe.py`).
- **Stress test** (`stress_probe.py`, 24 distinct 1×1 pieces around the house):
  - 21 models drawn at once (was 5), the rest pending
  - 39 KB of the ~47 KB texture pool used
  - 821 polygons / 1,864 vertices
  - still 20 fps
- Side by side with full resolution, the difference is hard to see at town scale (`build/screenshots/yardcmp.png`). Very fine details can be lost: the lamp's small top ornament turns white.
- The cache now has 24 slots.

### 2.3 ROM rebuild cost 12% of the ARM9 (fixed)
- The idle profile showed the hack at 47% idle with **no furniture**, against vanilla's 59%. Bisecting:
  - skipping each hook group changed nothing
  - a rebuild with **no patches at all** was still 47%
  - the cause was the build config: the earlier session had set `compressed: false` for arm9 and all 148 overlays
- With vanilla's compression flags restored, the rebuilt ROM is back to 59.2%, identical to vanilla.
- So the game reads overlays from the card during normal play, and larger uncompressed reads cost more ARM9 time than decompressing.
- `tools/build_rom.py` now always copies vanilla's `arm9.yaml` and `overlays.yaml`. This should also shorten load times on hardware.

### 2.4 Collision hook
- The PC profile (`pc_profile.py`) put ~5% of ARM9 instructions in the outdoor-furniture collision hook, mostly searching 8 neighbours for multi-square pieces on every empty square.
- That search is replaced by a per-frame list of covered squares filled by the draw hook.
- The measured gain was small: the cost really came from the rebuild issue in 2.3.

## 3. DSi / 3DS (research + reasoning)

Sources:
- GBATEK (local copy, `C:\NDS_RECOMP\prototype\docs-index\gbatek\dsi-control-registers-scfg.md`, `dsi-basic-differences-to-nds.md`)
- [nds-bootstrap glossary](https://wiki.ds-homebrew.com/nds-bootstrap/glossary)
- [ds-homebrew wiki source](https://git.randommeaninglesscharacters.com/rvtr/wiki/src/branch/main/pages/_nl-NL/nds-bootstrap/glossary.md)

What the DSi has, according to GBATEK:
- **CPU:** ARM9 at 134 MHz (SCFG_CLK bit 0).
- **RAM:** 16 MB main RAM (SCFG_EXT9 bits 14–15; mirrors at 0x0C000000).
- **Other:** new DMA (NDMA), revised geometry and renderer circuits, a DSP, the camera, and new shared WRAM.
- **VRAM is the same 656 KB.** "Extended VRAM access" (bit 13) changes access, not size.

What a DS game can actually use:
- **Real DSi or 3DS in NDS mode (cartridge, or the system launcher):** the firmware boots NDS games with SCFG_EXT9 = 0x03000000. That means 4 MB RAM, SCFG access disabled, original NDS BIOS. The game cannot reach any DSi feature.
- **nds-bootstrap / TWiLight Menu++ (SD card on DSi/3DS, some flashcarts):**
  - per-game "ARM9 CPU speed: 133 MHz (TWL)": the game simply runs faster
  - "VRAM mode: DSi" is documented as doing nothing useful
  - "Run in: DSi mode" has no effect for NDS-only ROMs
  - "ROM space in RAM / card read DMA" are loader-side load-time features, not memory the game sees
- **16 MB for the game itself:** it would need DSi mode with the RAM limit raised. AC:WW is an NTR (NDS-only) title whose code assumes the 4 MB map and mirrors (shared work area at 0x027FFxxx), so this would need a TWL header, signatures and relocations. Not realistic for this hack.

Would it help even if available?
- **CPU at 133 MHz:** the game is frame-capped at 20 fps and only ~41% busy in town, so no visible gain. At most a little more margin for heavy scenes.
- **More RAM:** RAM isn't the bottleneck. The heap has ~100 KB free in town, and a model needs ≤ 7 KB resident.
- **The outdoor furniture limit is texture VRAM,** which the DSi doesn't increase.
- **Conclusion:** DSi features don't solve this. The software fixes above (half-res, no thrash, compression) do, and they also run on an original DS and any flashcart.
- Optional future idea: detect TWL mode at runtime. SCFG_EXT9 at 0x04004008 reads 0 in NTR mode. When unlocked, the code could (if ever wanted) use the 0x0C400000+ RAM as a model-file cache to skip card reads. Low value, not implemented.

## 4. Further ideas (not done)
- **Distance LOD:** quarter resolution (16× less VRAM) for pieces more than ~6 squares away, re-uploaded at half resolution when the player comes close.
- **Better downsampling:** a palette-aware 2×2 box filter (average, then nearest palette entry) instead of nearest neighbour, to keep thin details like the lamp ornament.
- **Texture dedupe:** models of one furniture series that ship identical texture blocks could share one arena piece (needs a content hash per texture).
- **30 fps:** the game logic is fixed at 20 Hz, so a 30 fps mode would need delta-time logic or render interpolation. Out of scope for a QOL hack.
- **Code space:** about 1 KB of ITCM is left. The next feature needs another code home (`docs/REFERENCES.md` § Code space).
