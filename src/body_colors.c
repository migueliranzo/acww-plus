/*
 * AC:WW+ Shoe and sock colours (and the live body refresh used by the skin tone change).
 *
 * The body models (PBody/boy|grl.nsbmd) colour shoes and socks with their own palette "b1_pl":
 *   boy:  shoes 7..11 (a ramp from the colour to near white), socks 13
 *   girl: shoes 1 (colour), 3 (lighter), socks 15
 * In vanilla the sock texels share the white entry of the shoe trim (boy 12, girl 14), so tools/file_patches.py
 * (body_sock_index) moves them to the unused entry 13 / 15; recolouring keeps the shoe trim white.
 * (mapped in the emulator by recolouring texel regions, docs/features/shoes_socks.md).
 * Every player body is a per-player copy in RAM (player_body_cache) uploaded to its own VRAM slot, so the
 * entries are recoloured per player before upload. Choices live in the player record's PlayerTasks padding
 * (+0x1DD9: low nibble shoes, high nibble socks; 0 = the model's own colours).
 */
#include "acww.h"

#define FN_BODY_LOADER_ORIG         ((void (*)(u32 actor))(0x0200E18C | 1))
#define FN_BODY_BUF_GET             ((void *(*)(u8 *handle))(0x0205C890 | 1))
#define FN_BODY_TEX_ENTRY           ((u8 *(*)(u8 *handle))(0x0205C868 | 1))
#define FN_VRAM_SUBMIT_TEXLOAD      ((int (*)(u8 *entry, void *tex, int flag))(0x020B8EC4 | 1))
#define FN_NNS_G3D_GET_TEX_         ((u8 *(*)(void *file))0x02109680)
#define FN_PLAYER_IS_GIRL           ((int (*)(u32 actor))(0x02010DCC | 1))
#define FN_PLAYER_RECORD_OF_ACTOR   ((u8 *(*)(u32 actor))(0x02010DF4 | 1))
#define FN_PLAYER_PALETTE_IDS       ((void (*)(u32 actor, u32 hair, u32 tan))(0x0201014C | 1))
#define FN_PLAYER_HAIR_COLOUR       ((u32 (*)(u32 actor))(0x02010D5C | 1))
#define FN_PLAYER_COPY_PALETTE      ((void (*)(u32 actor, void *src_tex, void *dst_tex, const char *a, const char *b))(0x0200FB5C | 1))
#define FN_PALETTE_SKIN_BUF         ((void *(*)(u8 *palettes))(0x0205F170 | 1))

#define ACTOR_BODY_HANDLE           0x385
#define ACTOR_PALETTES              0x79C
#define PREC_LOOK_COLORS            0x1DD9   /* PlayerTasks pad_75 */

#define RGB5(r, g, b)               ((u16)(((r) >> 3) | (((g) >> 3) << 5) | (((b) >> 3) << 10)))

#define SHOE_PRESETS                12
#define SOCK_PRESETS                11

/* Index 0 = the model's own colours (not used from these tables). */
static const u16 s_shoe_colors[SHOE_PRESETS] = {
    0,
    RGB5(208, 24, 24),   /* red */
    RGB5(40, 40, 48),    /* black */
    RGB5(112, 64, 32),   /* brown */
    RGB5(200, 200, 200), /* white */
    RGB5(24, 152, 64),   /* green */
    RGB5(240, 200, 32),  /* yellow */
    RGB5(240, 112, 168), /* pink */
    RGB5(128, 56, 176),  /* purple */
    RGB5(32, 40, 112),   /* navy */
    RGB5(240, 120, 24),  /* orange */
    RGB5(72, 80, 240),   /* blue (the boy's own) */
};
static const u16 s_sock_colors[SOCK_PRESETS] = {
    0,
    RGB5(48, 48, 56),    /* black */
    RGB5(144, 144, 152), /* grey */
    RGB5(216, 40, 40),   /* red */
    RGB5(40, 56, 136),   /* navy */
    RGB5(248, 144, 192), /* pink */
    RGB5(248, 224, 64),  /* yellow */
    RGB5(48, 176, 88),   /* green */
    RGB5(128, 80, 40),   /* brown */
    RGB5(152, 88, 200),  /* purple */
    RGB5(120, 184, 248), /* sky blue */
};

/* Finds a palette by name in a TEX0 resource; returns its colours or 0. */
static u16 *tex_palette(u8 *tex, const char *name) {
    u8 *dict;
    u8 *info;
    u32 count, esz, i;
    u8 *entries;
    u8 *names;
    if (tex == 0) {
        return 0;
    }
    dict = tex + *(u16 *)(tex + 0x34);
    count = dict[1];
    info = dict + *(u16 *)(dict + 6);
    esz = *(u16 *)info;
    entries = info + 4;
    names = entries + count * esz;
    for (i = 0; i < count; i++) {
        const char *n = (const char *)(names + i * 16);
        int k = 0;
        while (k < 16 && name[k] != 0 && n[k] == name[k]) {
            k++;
        }
        if (name[k] == 0 && (k == 16 || n[k] == 0)) {
            u32 off = (u32)(*(u16 *)(entries + i * esz)) << 3;
            return (u16 *)(tex + *(u32 *)(tex + 0x38) + off);
        }
    }
    return 0;
}

/* c blended towards white by t/16 */
static u16 lighten(u16 c, int t) {
    int r = c & 31, g = (c >> 5) & 31, b = (c >> 10) & 31;
    r += ((31 - r) * t) >> 4;
    g += ((31 - g) * t) >> 4;
    b += ((31 - b) * t) >> 4;
    return (u16)(r | (g << 5) | (b << 10));
}

/* Writes the chosen shoe / sock colours into the actor's body palette (RAM copy). */
static void recolor_body(u32 actor) {
    static const char s_b1_pl[6] = { 'b', '1', '_', 'p', 'l', 0 };
    u8 *handle = (u8 *)(actor + ACTOR_BODY_HANDLE);
    u8 *rec = FN_PLAYER_RECORD_OF_ACTOR(actor);
    u8 *tex;
    u16 *pal;
    u32 shoes, socks;
    if (rec == 0) {
        return;
    }
    shoes = rec[PREC_LOOK_COLORS] & 0xF;
    socks = rec[PREC_LOOK_COLORS] >> 4;
    if (shoes >= SHOE_PRESETS) {
        shoes = 0;
    }
    if (socks >= SOCK_PRESETS) {
        socks = 0;
    }
    if (shoes == 0 && socks == 0) {
        return; /* the file's own palette was just loaded / is unchanged */
    }
    tex = FN_NNS_G3D_GET_TEX_(FN_BODY_BUF_GET(handle));
    pal = tex_palette(tex, s_b1_pl);
    if (pal == 0) {
        return;
    }
    if (FN_PLAYER_IS_GIRL(actor)) {
        if (shoes) {
            pal[1] = s_shoe_colors[shoes];
            pal[3] = lighten(s_shoe_colors[shoes], 5);
        }
        if (socks) {
            pal[15] = s_sock_colors[socks];
        }
    } else {
        if (shoes) {
            static const u8 s_ramp[5] = { 0, 3, 7, 10, 13 };
            int i;
            for (i = 0; i < 5; i++) {
                pal[7 + i] = lighten(s_shoe_colors[shoes], s_ramp[i]);
            }
        }
        if (socks) {
            pal[13] = s_sock_colors[socks];
        }
    }
}

/*
 * Rebuilds the body palettes of a player (the model's shoe / sock colours, then the choice, then the skin
 * palette for the tone) and queues the VBlank upload of its body texture. Used after a change on the phone.
 */
void body_colors_refresh(u32 actor, u32 tone) {
    static const char s_skin_pl[8] = { 's', 'k', 'i', 'n', '_', 'p', 'l', 0 };
    static const char s_b1_pl[6] = { 'b', '1', '_', 'p', 'l', 0 };
    static const u16 s_boy[9] = { RGB5(72, 80, 240), RGB5(104, 112, 240), RGB5(152, 160, 240),
                                  RGB5(184, 184, 248), RGB5(216, 216, 248), RGB5(248, 248, 248),
                                  RGB5(248, 248, 248), RGB5(248, 248, 248), RGB5(248, 248, 248) };
    u8 *handle = (u8 *)(actor + ACTOR_BODY_HANDLE);
    u8 *entry = FN_BODY_TEX_ENTRY(handle);
    u8 *tex = FN_NNS_G3D_GET_TEX_(FN_BODY_BUF_GET(handle));
    u16 *pal = tex_palette(tex, s_b1_pl);
    int i;
    if (entry == 0 || tex == 0) {
        return;
    }
    if (pal != 0) {
        if (FN_PLAYER_IS_GIRL(actor)) {
            pal[1] = RGB5(248, 0, 0);
            pal[3] = RGB5(248, 80, 80);
            pal[14] = RGB5(248, 248, 248);
            pal[15] = RGB5(248, 248, 248);
        } else {
            for (i = 0; i < 9; i++) {
                pal[7 + i] = s_boy[i];
            }
        }
    }
    recolor_body(actor);
    /* skin: re-read the skin / hair palettes for the tone, copy skin_pl into the body texture */
    FN_PLAYER_PALETTE_IDS(actor, FN_PLAYER_HAIR_COLOUR(actor), tone);
    FN_PLAYER_COPY_PALETTE(actor, FN_NNS_G3D_GET_TEX_(FN_PALETTE_SKIN_BUF((u8 *)(actor + ACTOR_PALETTES))), tex,
                           s_skin_pl, s_skin_pl);
    if (entry[0xD] != 1) {
        FN_VRAM_SUBMIT_TEXLOAD(entry, tex, 1);
    }
}

/* Steps the shoe (which = 0) or sock (which = 1) colour of the player with record rec. */
void body_colors_step(u8 *rec, int which) {
    u32 v = rec[PREC_LOOK_COLORS];
    u32 s;
    if (which == 0) {
        s = (v & 0xF) + 1;
        if (s >= SHOE_PRESETS) {
            s = 0;
        }
        v = (v & 0xF0) | s;
    } else {
        s = (v >> 4) + 1;
        if (s >= SOCK_PRESETS) {
            s = 0;
        }
        v = (v & 0x0F) | (s << 4);
    }
    rec[PREC_LOOK_COLORS] = (u8)v;
}

/* Hook: player actor init's call of player_body_loader (0x0200DF10). Recolours before the first upload. */
void hook_player_body_loader(u32 actor) {
    FN_BODY_LOADER_ORIG(actor);
    recolor_body(actor);
}
