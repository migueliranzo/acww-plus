/*
 * AC:WW+ Transparent colour in patterns (designs).
 *
 * Palette index 0 is black (0x0000) in all 16 design palettes and vanilla never uses it: the editor offers
 * colours 1..15 only. In the editor (ov123), L/R now cycle through 0 as well (patched in tools/patches.py);
 * index 0 is the transparent colour.
 * The 32 player design textures (design_textures_build, table 0x021CF428) get the TEXIMAGE "colour 0 is
 * transparent" bit, so transparent pixels show what is behind: the ground under a design laid on the ground,
 * see-through spots on an umbrella. Worn shirts are composited into the body texture (opaque, unchanged).
 */
#include "acww.h"

#define FN_TEX_VRAM_ALLOC_LOAD      ((u32 (*)(void *tex_res, void *keys))(0x02055920 | 1))
#define TEXIMAGE_COLOR0_TRANSPARENT 0x20000000

/* Sets the colour-0 transparency bit of every texture in a TEX0 resource. */
static void tex_color0_transparent(u8 *tex) {
    u8 *dict = tex + *(u16 *)(tex + 0x0E);
    u32 count = dict[1];
    u8 *info = dict + *(u16 *)(dict + 6);
    u32 esz = *(u16 *)info;
    u32 i;
    for (i = 0; i < count; i++) {
        *(u32 *)(info + 4 + i * esz) |= TEXIMAGE_COLOR0_TRANSPARENT;
    }
}

/* Hook: design_textures_build's upload of each player design texture (0x02071864). */
u32 hook_design_tex_upload(void *tex_res, void *keys) {
    if (tex_res != 0) {
        tex_color0_transparent((u8 *)tex_res);
    }
    return FN_TEX_VRAM_ALLOC_LOAD(tex_res, keys);
}
