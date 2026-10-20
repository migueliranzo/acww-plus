/*
 * AC:WW+ Outdoor Furniture
 * Compiled with Metrowerks CodeWarrior (mwccarm.exe -O4,s -inline off -proc arm946e -thumb -interworking)
 * Linked at 0x01FFDC00 (unused ITCM tail: 0x01FFDAE0..0x02000000).
 *
 * Furniture dropped outdoors (item ids 0x3000..0x4BA3 on the town grid) is drawn as its real 3D model,
 * is solid, keeps the player's facing, and covers its full footprint (1x1, 2x1 rotated, 2x2).
 * Secondary squares of multi-square pieces hold 0xF031, the same marker the game uses in house rooms.
 */

#include "ftr_shared.h"
#include "code_home.h"

static OutdoorFtrCache *s_cache;
static u16 s_dropping_item; /* furniture id being dropped from the pockets (0 = none) */
u32 g_ftr_perf[4];          /* perf counters: models loaded, evictions, loads refused, draws */
u32 g_ftr_dbg[4];           /* debug counters: shape calls, furniture hits, markers written, markers cleared */

/* Collision cylinder for outdoor furniture: radius=0x0C, height=0x10, kind=0x06 */
static const u8 s_furniture_shape[4] = { 0x0C, 0x10, 0x06, 0x00 };

/* Light-source models: ftr_info indoor.bin byte 1 bit 4/5 (furniture_model_flag4_5), same in all 5 languages.
 * exotic, regal, cabana, green, modern, lovely, robo-, snowman, mush lamps, blue dresser, mush stand, lantern,
 * table lamp, desk light, candle, mini-lamp, festive candle. */
static const u16 s_light_models[17] = {
    0x007, 0x024, 0x031, 0x038, 0x043, 0x059, 0x06D, 0x077, 0x081, 0x089, 0x08A, 0x17F, 0x209, 0x20A, 0x20B, 0x20C, 0x20E
};
#define LAMP_NIGHT_EMI              0x4B9F   /* warm white (RGB555 31,28,18) */

/* Lamps glow from 18:00 to 06:00 (the hours the town's own lights are on). */
static int lamp_glows(u16 model_id) {
    u32 h = *GAME_HOUR_ADDR;
    int i;
    if (h >= 6 && h < 18) {
        return 0;
    }
    for (i = 0; i < 17; i++) {
        if (s_light_models[i] == model_id) {
            return 1;
        }
    }
    return 0;
}

static int is_furniture_item(u16 item) {
    return (item >= FTR_ITEM_MIN && item < FTR_ITEM_MAX_EXCL);
}

/* ------------------------------------------------------------------------- */
/* Town grid helpers                                                          */
/* ------------------------------------------------------------------------- */

static u16 *town_tile(int ux, int uz) {
    u32 map = *TOWN_MAP_PTR_ADDR;
    if (map == 0 || ux < 0 || uz < 0) {
        return 0;
    }
    return FN_TOWN_ITEM_ON_TILE(map, ux >> 4, uz >> 4, ux & 15, uz & 15, 0);
}

/* Grid coordinates of a town grid cell pointer: acre-major 4x4 acres of 16x16. 0 when outside. */
static int grid_coords(const u16 *t, int *gx, int *gz) {
    u32 idx = (u32)((const u8 *)t - (const u8 *)TOWN_GRID_RAM) >> 1;
    if ((const u8 *)t < (const u8 *)TOWN_GRID_RAM || idx >= 16 * 256) {
        return 0;
    }
    *gx = (int)(((idx >> 8) & 3) * 16 + (idx & 15));
    *gz = (int)((idx >> 10) * 16 + ((idx >> 4) & 15));
    return 1;
}

static void update_player_tile(OutdoorFtrCache *c) {
    u32 actor = FN_GET_PLAYER_ACTOR(4);
    int ux, uz;
    u16 *t;
    c->player_gx = -1000;
    c->player_gz = -1000;
    if (actor == 0) {
        return;
    }
    FN_POS_TO_UNIT_XZ(&ux, &uz, (const void *)(actor + 0x5C));
    t = town_tile(ux, uz);
    if (t != 0) {
        grid_coords(t, &c->player_gx, &c->player_gz);
    }
}

static u32 tile_distance(OutdoorFtrCache *c, const u16 *t) {
    int gx, gz, dx, dz;
    if (!grid_coords(t, &gx, &gz)) {
        return 255;
    }
    dx = gx - c->player_gx;
    dz = gz - c->player_gz;
    if (dx < 0) dx = -dx;
    if (dz < 0) dz = -dz;
    dx = dx > dz ? dx : dz;
    return dx > 255 ? 255 : (u32)dx;
}

/* Footprint helper object: { footprint kind, facing } (8 bytes, see furniture_footprint_ctor). */
static u32 footprint_init(u32 *fp, const u16 *item_ptr) {
    FN_FTPRINT_CTOR(fp, item_ptr);
    return FN_FTPRINT_COUNT(fp);
}

/* Writes 0xF031 into the empty secondary squares of the multi-square piece at (ux, uz). */
static void ensure_markers(const u16 *anchor, int ux, int uz) {
    u32 fp[2];
    u32 n = footprint_init(fp, anchor);
    u32 i;
    for (i = 1; i < n; i++) {
        const s16 *sq = FN_FTPRINT_SQUARE(fp, i);
        u16 *t = town_tile(ux + sq[0], uz + sq[1]);
        if (t != 0 && *t == ITEM_EMPTY) {
            *t = ITEM_FTR_COVERED;
            g_ftr_dbg[2]++;
        }
    }
}

/*
 * Furniture that fell out of a shaken tree stays a leaf (vanilla look, no collision): its square is remembered here
 * (grid index + 1, 0 = free) until the square stops holding furniture. RAM only: after a save and reload an unpicked
 * tree drop shows as 3D furniture.
 */
#define LEAF_MAX 8
static u16 s_leaf[LEAF_MAX];
static u8 s_leaf_next;

static int leaf_has(const u16 *t) {
    u32 idx = ((u32)((const u8 *)t - (const u8 *)TOWN_GRID_RAM) >> 1) + 1;
    int i;
    for (i = 0; i < LEAF_MAX; i++) {
        if (s_leaf[i] == idx) {
            return 1;
        }
    }
    return 0;
}

/* Forgets squares that no longer hold furniture (the leaf was picked up). */
static void leaf_purge(void) {
    int i;
    for (i = 0; i < LEAF_MAX; i++) {
        if (s_leaf[i] != 0 && !is_furniture_item(((const u16 *)TOWN_GRID_RAM)[s_leaf[i] - 1])) {
            s_leaf[i] = 0;
        }
    }
}

/*
 * Squares covered by multi-square pieces, collected by the draw hook (every furniture piece in view is drawn
 * each frame), double buffered per frame. The collision hook looks squares up here instead of searching the
 * 8 neighbours of every empty square it is asked about (that search cost ~10% of the ARM9 in town).
 * Each entry is { square, anchor } as town grid indices. The list only turns over while furniture is drawn, so
 * once the last piece in view is picked up it goes stale: an entry counts only while its anchor still holds
 * furniture (otherwise the picked-up piece's second square stayed solid and invisible).
 */
#define COVER_MAX 48
static u16 s_cover[2][COVER_MAX][2];
static u8 s_cover_n[2];
static u8 s_cover_cur;
static u8 s_cover_valid;
static u32 s_cover_tag = 0xFFFFFFFF;

static void cover_frame(u32 ctx) {
    u32 tag = *(volatile u32 *)(ctx + 0x6A6C);
    if (tag != s_cover_tag) {
        s_cover_tag = tag;
        s_cover_cur ^= 1;
        s_cover_n[s_cover_cur] = 0;
        s_cover_valid = 1;
        leaf_purge();
    }
}

static void cover_add(const u16 *anchor) {
    u32 fp[2];
    u32 n = footprint_init(fp, anchor);
    u32 i;
    int gx, gz;
    if (n < 2 || !grid_coords(anchor, &gx, &gz)) {
        return;
    }
    for (i = 1; i < n && s_cover_n[s_cover_cur] < COVER_MAX; i++) {
        const s16 *sq = FN_FTPRINT_SQUARE(fp, i);
        int x = gx + sq[0];
        int z = gz + sq[1];
        u16 *e;
        if ((u32)x >= 64 || (u32)z >= 64) {
            continue;
        }
        e = s_cover[s_cover_cur][s_cover_n[s_cover_cur]++];
        e[0] = (u16)((((z >> 4) << 2) + (x >> 4)) * 256 + (z & 15) * 16 + (x & 15));
        e[1] = (u16)(((const u8 *)anchor - (const u8 *)TOWN_GRID_RAM) >> 1);
    }
}

/* True when a furniture piece drawn this or the last frame covers the square at t and is still there. */
static int cover_has(const u16 *t) {
    u32 idx = (u32)((const u8 *)t - (const u8 *)TOWN_GRID_RAM) >> 1;
    int b, i;
    for (b = 0; b < 2; b++) {
        for (i = 0; i < s_cover_n[b]; i++) {
            if (s_cover[b][i][0] == idx && is_furniture_item(((const u16 *)TOWN_GRID_RAM)[s_cover[b][i][1]])) {
                return 1;
            }
        }
    }
    return 0;
}

/* ------------------------------------------------------------------------- */
/* Model cache                                                                */
/* ------------------------------------------------------------------------- */

static OutdoorFtrCache *get_or_create_cache(u32 root_heap, u32 ctx) {
    int i;
    OutdoorFtrCache *c = s_cache;
    if (c != 0 && c->magic == CACHE_MAGIC && c->owner_ctx == ctx) {
        return c;
    }
    /* A cache from another scene instance (teardown hook missed) is abandoned, never touched. */
    s_cache = 0;
    if (FN_HEAP_ALLOCATABLE(root_heap, 4) < sizeof(OutdoorFtrCache) + HEAP_MIN_FREE) {
        return 0;
    }
    c = (OutdoorFtrCache *)FN_HEAP_ALLOC(root_heap, sizeof(OutdoorFtrCache));
    if (c == 0) {
        return 0;
    }
    c->magic = CACHE_MAGIC;
    c->tick_counter = 1;
    c->last_raw_tag = 0xFFFFFFFF;
    c->frame_seq = 1;
    c->owner_ctx = ctx;
    c->heap_free_seen = 0;
    c->fail_count = 0;
    c->retry_seq = 1 + ARENA_DELAY_FRAMES;
    c->neg_model = 0xFFFF;
    c->neg_seq = 0;
    for (i = 0; i < NUM_ARENAS; i++) {
        c->arena_key[i] = 0;
        c->arena_size[i] = 0;
    }
    c->pltt_key = 0;
    c->vram_claimed = 0;
    c->player_gx = -1000;
    c->player_gz = -1000;
    for (i = 0; i < MAX_FTR_SLOTS; i++) {
        int j;
        c->slots[i].model_id = 0xFFFF;
        c->slots[i].btx_buf = 0;
        FN_VRAM_REQ_CTOR(c->slots[i].req);
        c->slots[i].arena = 0;
        c->slots[i].dist = 0;
        c->slots[i].tex_off = 0;
        c->slots[i].tex_size = 0;
        c->slots[i].last_used_tick = 0;
        c->slots[i].last_frame_seq = 0;
        c->slots[i].arc_buf = 0;
        c->slots[i].mdl_ptr = 0;
        for (j = 0; j < 5; j++) {
            c->slots[i].vram_slot[j] = 0;
        }
    }
    s_cache = c;
    return c;
}

static void slot_release_model(OutdoorFtrSlot *slot, u32 root_heap) {
    if (REQ_PENDING(slot)) {
        FN_VRAM_REQ_CANCEL(slot->req);
    }
    if (slot->btx_buf != 0) {
        FN_HEAP_FREE(root_heap, slot->btx_buf);
    }
    slot->btx_buf = 0;
    if (slot->arc_buf != 0) {
        FN_HEAP_FREE(root_heap, slot->arc_buf);
    }
    slot->arc_buf = 0;
    slot->mdl_ptr = 0;
    slot->model_id = 0xFFFF;
}

static int draw_outdoor_furniture(u32 ctx, const u16 *item_ptr, const u32 *mtx_src) {
    u32 root_heap = *ROOT_HEAP_PTR_ADDR;
    u16 item = *item_ptr;
    OutdoorFtrCache *cache;
    u16 model_id;
    u32 facing;
    int i;
    int slot_idx = -1;
    u32 raw_tag;
    OutdoorFtrSlot *slot;
    u32 *mtx_dst;
    u32 fp[2];
    u32 dist;
    u16 emi;

    if (root_heap == 0 || !hx_ready()) {
        return 0;
    }
    cache = get_or_create_cache(root_heap, ctx);
    if (cache == 0) {
        return 0;
    }

    raw_tag = *(volatile u32 *)(ctx + 0x6A6C);
    if (raw_tag != cache->last_raw_tag) {
        cache->last_raw_tag = raw_tag;
        cache->frame_seq++;
        update_player_tile(cache);
    }
    dist = tile_distance(cache, item_ptr);

    model_id = (u16)((item - FTR_ITEM_MIN) >> 2);
    if (model_id >= 0x6E9) {
        return 0;
    }

    for (i = 0; i < MAX_FTR_SLOTS; i++) {
        if (cache->slots[i].model_id == model_id && cache->slots[i].mdl_ptr != 0) {
            slot_idx = i;
            break;
        }
    }
    if (slot_idx < 0) {
        /* Loads wait until the scene settled, then back off after a refusal (no per-frame file reads) */
        if (cache->frame_seq < cache->retry_seq) {
            return 0;
        }
        if (!cache->vram_claimed) {
            ((void (*)(OutdoorFtrCache *))g_hx_fn[HX_CLAIM_VRAM])(cache);
        }
        if (model_id == cache->neg_model && cache->frame_seq < cache->neg_seq) {
            return 0;
        }
        if (!((int (*)(OutdoorFtrCache *, u32))g_hx_fn[HX_CAN_PLACE])(cache, dist)) {
            return 0;
        }
        /* At most one load per frame: each load reads two files from the card */
        cache->retry_seq = cache->frame_seq + 1;
        slot_idx = ((int (*)(OutdoorFtrCache *, u16, u32, u32))g_hx_fn[HX_LOAD_MODEL])(cache, model_id, root_heap, dist);
        if (slot_idx < 0) {
            cache->fail_count++;
            cache->neg_model = model_id;
            cache->neg_seq = cache->frame_seq + RETRY_DELAY_FRAMES;
            return 0;
        }
    }

    slot = &cache->slots[slot_idx];
    slot->last_used_tick = ++cache->tick_counter;
    if (slot->last_frame_seq != cache->frame_seq || dist < slot->dist) {
        slot->dist = (u8)dist;
    }
    slot->last_frame_seq = cache->frame_seq;
    if (slot->btx_buf != 0) {
        if (REQ_PENDING(slot)) {
            return 0; /* texture not in VRAM yet: leaf this frame */
        }
        FN_HEAP_FREE(root_heap, slot->btx_buf);
        slot->btx_buf = 0;
    }

    /* Copy the drum-bent tile matrix (rows 0-2 basis, row 3 translation, fx32) into mdl_obj + 0x64 */
    mtx_dst = &slot->mdl_obj[0x64 / 4];
    for (i = 0; i < 12; i++) {
        mtx_dst[i] = mtx_src[i];
    }
    /* 2x2 pieces sit on the corner shared by their four squares (+half a square in x and z) */
    footprint_init(fp, item_ptr);
    if (fp[0] == 2) {
        for (i = 0; i < 3; i++) {
            mtx_dst[9 + i] += mtx_dst[0 + i] + mtx_dst[6 + i]; /* 0x1000 * basis (fx32 1.0) */
        }
    }
    facing = (u32)(item & 3);
    if (facing != 0) {
        FN_MTX_ROTATE_Y_MODEL(mtx_dst, facing << 14);
    }

    emi = lamp_glows(model_id) ? LAMP_NIGHT_EMI : FN_LIGHT_SLOT2_TO_EMI();
    FN_NNS_G3D_SET_EMI_ALL(slot->mdl_ptr, emi);
    FN_MDL_OBJ_DRAW(slot->mdl_obj, 0);
    return 1;
}

/* ------------------------------------------------------------------------- */
/* Hooks                                                                      */
/* ------------------------------------------------------------------------- */

/*
 * Hook 1: Called from ov003_item_draw_loop at 0x022212C2 (r0 = r7 frame pointer).
 * Renders Category 3/4 furniture as 3D models; falls back to the vanilla icon renderer for Category 1 or on failure.
 */
void hook_ov003_draw_item(u8 *r7_frame) {
    u32 ctx = *(u32 *)(r7_frame + 0x00);
    const u16 *item_ptr = *(const u16 **)(r7_frame + 0x90);
    const u32 *mtx_src = (const u32 *)(r7_frame + 0xD8);
    int icon_id;
    u32 *mdl_obj;
    int i;

    if (is_furniture_item(*item_ptr)) {
        cover_frame(ctx);
        if (leaf_has(item_ptr)) {
            goto icon;
        }
        cover_add(item_ptr);
        if (draw_outdoor_furniture(ctx, item_ptr, mtx_src)) {
            return;
        }
    }

icon:
    /* Vanilla icon path (equivalent to 0x022212C0..0x022212F6 + ov003_item_render) */
    icon_id = FN_ITEM_ICON_ID(item_ptr);
    *(u32 *)(r7_frame + 0x08) = (u32)icon_id;
    mdl_obj = *(u32 **)(ctx + icon_id * 4 + 0x50);
    if (mdl_obj != 0) {
        u32 *mtx_dst = &mdl_obj[0x64 / 4];
        u16 emi;
        for (i = 0; i < 12; i++) {
            mtx_dst[i] = mtx_src[i];
        }
        FN_MDL_OBJ_DRAW_SIMPLE(mdl_obj, 0);
        emi = FN_LIGHT_SLOT2_TO_EMI();
        FN_NNS_G3D_SET_EMI_ALL((void *)mdl_obj[0x5C / 4], emi);
    }
}

/*
 * Hook 2: Called from func_ov003_02220aa8 at 0x02220ADA during outdoor scene teardown.
 * Frees all heap allocations owned by OutdoorFtrCache before calling the original teardown callee.
 * (VRAM slots come from the scene's frame VRAM manager, which the scene resets itself.)
 */
void hook_ov003_teardown(void) {
    OutdoorFtrCache *c = s_cache;
    u32 root_heap = *ROOT_HEAP_PTR_ADDR;
    if (c != 0 && c->magic == CACHE_MAGIC && root_heap != 0) {
        int i;
        for (i = 0; i < MAX_FTR_SLOTS; i++) {
            slot_release_model(&c->slots[i], root_heap);
        }
        c->magic = 0;
        FN_HEAP_FREE(root_heap, c);
    }
    s_cache = 0;
    FN_OV003_TEARDOWN_SUB();
}

/*
 * Hook 3: replaces town_query_item_shape's call of ov003_item_shape (arm9 0x020B2A90).
 * Called by the walker collision gather (0x0203259c) for every unit in the walker's box; returns the collision cylinder of the item on (ux, uz).
 * Furniture and the squares it covers (0xF031) are solid. Missing markers are written, orphaned ones cleared.
 */
int hook_ov003_item_shape(u32 unused, int *radius, int *height, u32 *kind, int ux, int uz) {
    u16 *item_ptr;
    const u8 *shape;
    u16 item;

    if (*TOWN_MAP_PTR_ADDR == 0) {
        return 0;
    }
    item_ptr = town_tile(ux, uz);
    if (item_ptr == 0) {
        return 0;
    }
    item = *item_ptr;
    g_ftr_dbg[0]++;
    if (is_furniture_item(item) && !leaf_has(item_ptr)) {
        g_ftr_dbg[1]++;
        ensure_markers(item_ptr, ux, uz);
        shape = s_furniture_shape;
    } else if (item == ITEM_EMPTY) {
        /* A secondary square can be queried before its anchor: mark it as soon as it is seen */
        if (!cover_has(item_ptr)) {
            return 0;
        }
        *item_ptr = ITEM_FTR_COVERED;
        g_ftr_dbg[2]++;
        shape = s_furniture_shape;
    } else if (item == ITEM_FTR_COVERED) {
        if (s_cover_valid && !cover_has(item_ptr)) {
            g_ftr_dbg[3]++;
            *item_ptr = ITEM_EMPTY;
            return 0;
        }
        shape = s_furniture_shape;
    } else {
        shape = FN_OV003_SHAPE_LOOKUP_ORIG(item_ptr);
    }
    if (shape == 0 || shape[2] == 0) {
        return 0;
    }
    *radius = (int)((u32)shape[0] << 12) >> 4;
    *height = (int)((u32)shape[1] << 12) >> 4;
    *kind = shape[2];
    return 1;
}

/*
 * Hook 4: Called from func_02042d8c at 0x02042DB4 when dropping an item outdoors.
 * Encodes the player's cardinal facing direction into the bottom 2 bits (item & 3) for furniture items.
 */
u32 hook_outdoor_drop_item(u32 player_idx, int action_kind, u32 item_id) {
    u16 id = (u16)item_id;
    u32 ret;
    if (is_furniture_item(id)) {
        u32 actor = FN_GET_PLAYER_ACTOR(4);
        if (actor != 0) {
            u16 angle = *(volatile u16 *)(actor + 0x8E);
            u32 facing = ((u32)(angle + 0x2000) >> 14) & 3;
            id = (u16)((id & ~3) | facing);
        }
        s_dropping_item = id;
        leaf_purge(); /* a leaf picked up from the target square must not turn this piece into a leaf */
    }
    ret = FN_OUTDOOR_DROP_HELPER(player_idx, action_kind, (u32)id);
    s_dropping_item = 0;
    return ret;
}

/*
 * Hook 5: Called from field_put_spot_find at 0x02042B7A for each candidate drop unit.
 * While a multi-square piece is being dropped, a candidate only passes if all of its squares pass.
 */
u16 *hook_field_put_spot_check(u32 kind, u32 map, int ux, int uz, int *from) {
    u16 *t = FN_FIELD_PUT_SPOT_CHECK(kind, map, ux, uz, from);
    if (t != 0 && s_dropping_item != 0 && *t == ITEM_EMPTY) {
        u32 fp[2];
        u32 n = footprint_init(fp, &s_dropping_item);
        u32 i;
        for (i = 1; i < n; i++) {
            const s16 *sq = FN_FTPRINT_SQUARE(fp, i);
            u16 *s = FN_FIELD_PUT_SPOT_CHECK(kind, map, ux + sq[0], uz + sq[1], from);
            if (s == 0 || *s != ITEM_EMPTY) {
                return 0;
            }
        }
    }
    return t;
}

/*
 * Hook 6: tree_shake_nonfruit_drop's item-put request (arm9 0x02044CEA -> 0x020457B4).
 * Furniture shaken out of a tree is remembered so it keeps the vanilla leaf look.
 */
u32 hook_tree_drop_item(u32 player, int *unit_xz, u32 item, u32 expect, u32 a5, u32 a6, u32 a7, u32 a8, u32 a9, int a10) {
    if (is_furniture_item((u16)item)) {
        u16 *t = town_tile(unit_xz[0], unit_xz[1]);
        if (t != 0 && !leaf_has(t)) {
            leaf_purge();
            s_leaf[s_leaf_next] = (u16)((((const u8 *)t - (const u8 *)TOWN_GRID_RAM) >> 1) + 1);
            s_leaf_next = (u8)((s_leaf_next + 1) & (LEAF_MAX - 1));
        }
    }
    return FN_FIELD_ITEM_PUT_REQ(player, unit_xz, item, expect, a5, a6, a7, a8, a9, a10);
}

