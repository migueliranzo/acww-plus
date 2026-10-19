/*
 * AC:WW+ Outdoor Furniture
 * Compiled with Metrowerks CodeWarrior (mwccarm.exe -O4,s -inline off -proc arm946e -thumb -interworking)
 * Linked at 0x01FFDC00 (unused ITCM tail: 0x01FFDAE0..0x02000000).
 *
 * Furniture dropped outdoors (item ids 0x3000..0x4BA3 on the town grid) is drawn as its real 3D model,
 * is solid, keeps the player's facing, and covers its full footprint (1x1, 2x1 rotated, 2x2).
 * Secondary squares of multi-square pieces hold 0xF031, the same marker the game uses in house rooms.
 */

typedef unsigned char      u8;
typedef unsigned short     u16;
typedef unsigned int       u32;
typedef signed short       s16;
typedef signed int         s32;

/* --- Vanilla Engine Function Pointers (EU ADMP) --- */

/* ARM functions in main / SDK */
#define FN_HEAP_ALLOC               ((void *(*)(u32 heap, u32 size))0x020E9288)
#define FN_HEAP_FREE                ((void (*)(u32 heap, void *ptr))0x020E927C)
#define FN_HEAP_ALLOCATABLE         ((u32 (*)(u32 heap, int align))0x020E96A4)
#define FN_MTX_ROTATE_Y_MODEL       ((void (*)(void *mtx43, u32 angle))0x020E9084)
#define FN_NNS_FND_MOUNT_ARCHIVE    ((int (*)(void *archive, const char *name, void *arc_buf))0x02104724)
#define FN_NNS_FND_GET_ARC_FILE     ((void *(*)(const char *path))0x021046A0)
#define FN_NNS_FND_UNMOUNT_ARCHIVE  ((int (*)(void *archive))0x021046F4)
#define FN_NNS_G3D_PLTT_REQ_SIZE    ((u32 (*)(const void *tex_res))0x02107018)
#define FN_NNS_G3D_TEX4X4_REQ_SIZE  ((u32 (*)(const void *tex_res))0x02107114)
#define FN_NNS_G3D_TEX_REQ_SIZE     ((u32 (*)(const void *tex_res))0x02107120)
#define FN_NNS_G3D_SET_EMI_ALL      ((void (*)(void *mdl_ptr, u16 emi))0x021093BC)
#define FN_NNS_G3D_GET_TEX          ((void *(*)(void *btx_file))0x02109680)
#define FN_NNS_G3D_GET_MDL_SET      ((u8 *(*)(void *bmd_file))0x021096C0)

/* Thumb functions in main / ov003 (bit 0 = 1) */
#define FN_OUTDOOR_DROP_HELPER      ((u32 (*)(u32 player, int kind, u32 item_id))(0x02042DC4 | 1))
#define FN_FIELD_PUT_SPOT_CHECK     ((u16 *(*)(u32 kind, u32 map, int ux, int uz, int *from))(0x02042C14 | 1))
#define FN_OV003_TEARDOWN_SUB       ((void (*)(void))(0x020454D4 | 1))
#define FN_ITEM_ICON_ID             ((int (*)(const u16 *item_ptr))(0x0204BD5C | 1))
#define FN_POS_TO_UNIT_XZ           ((void (*)(int *ux, int *uz, const void *pos))(0x0204EF38 | 1))
#define FN_TOWN_ITEM_ON_TILE        ((u16 *(*)(u32 map, int ax, int az, int lx, int lz, int layer))(0x0204ED00 | 1))
#define FN_FTPRINT_SQUARE           ((const s16 *(*)(void *fp, u32 idx))(0x020525E8 | 1))
#define FN_FTPRINT_COUNT            ((u32 (*)(void *fp))(0x02052648 | 1))
#define FN_FTPRINT_CTOR             ((void *(*)(void *fp, const u16 *item_ptr))(0x02052664 | 1))
#define FN_MDL_OBJ_INIT             ((void *(*)(void *mdl_obj))(0x02055038 | 1))
#define FN_VRAM_SLOT_ALLOC          ((void (*)(void *vram_slot, int tex_sz, int tex4x4_sz, int pltt_sz))(0x0205553C | 1))
#define FN_VRAM_SLOT_INIT           ((void *(*)(void *vram_slot))(0x020555B0 | 1))
#define FN_MDL_OBJ_DRAW             ((void (*)(void *mdl_obj, void *scale_or_0))(0x02055738 | 1))
#define FN_MDL_OBJ_DRAW_SIMPLE      ((void (*)(void *mdl_obj, void *scale_or_0))(0x0205574C | 1))
#define FN_MODEL_BIND               ((int (*)(void *mdl_obj, void *mdl_ptr, void *tex_res))(0x020557FC | 1))
#define FN_TEX_UPLOAD_TO_SLOT       ((u32 (*)(void *tex_res, void *vram_slot))(0x02055920 | 1))
#define FN_FS_LOAD_DECOMPRESS       ((void *(*)(const char *path, u32 heap, int align, u32 *out_sz))(0x02064490 | 1))
#define FN_LIGHT_SLOT2_TO_EMI       ((u16 (*)(void))(0x02064F68 | 1))
#define FN_GET_PLAYER_ACTOR         ((u32 (*)(int idx))(0x02095550 | 1))
#define FN_OV003_SHAPE_LOOKUP_ORIG  ((const u8 *(*)(const u16 *item_ptr))(0x022235BC | 1))

/* Global Engine Addresses */
#define ROOT_HEAP_PTR_ADDR          ((volatile u32 *)0x021F7ECC)
#define TOWN_MAP_PTR_ADDR           ((volatile u32 *)0x021C7BA4)
#define TOWN_GRID_RAM               0x021E6D4C   /* 16 acres x 16x16 u16 (save 0xC354), acre-major */
#define VRAM_PAL_CUR_ADDR           ((volatile u32 *)0x021F2CB0)
#define VRAM_TEX_HI_ADDR            ((volatile u32 *)0x021F2CB4) /* 4 regions, hi bounds */
#define VRAM_TEX_LO_ADDR            ((volatile u32 *)0x021F2CC4) /* 4 regions, lo bounds */
#define VRAM_PAL_END_ADDR           ((volatile u32 *)0x021F2CD4)

/* Item ids */
#define FTR_ITEM_MIN                0x3000
#define FTR_ITEM_MAX_EXCL           0x4BA4
#define ITEM_EMPTY                  0xFFF1
#define ITEM_FTR_COVERED            0xF031

/* Budgets */
#define MAX_FTR_SLOTS               12
#define NUM_ARENAS                  2
#define TEX_ALIGN                   0x40     /* sub-allocation granule inside an arena */
#define PLTT_SLOT_SIZE              0x80     /* every ftr palette is <= 0x80 bytes (ROM survey) */
#define VRAM_TEX_RESERVE            0x200    /* per region, texture VRAM left free for the game */
#define VRAM_PLTT_RESERVE           0x400
#define MIN_ARENA_SIZE              0x1000
#define MAX_ARENA_SIZE              0x8000
#define HEAP_MIN_FREE               0xC000   /* largest free block needed before loading a model */
#define ARENA_DELAY_FRAMES          30       /* frames after the first draw before VRAM is claimed */
#define RETRY_DELAY_FRAMES          20       /* frames to wait after a load was refused */
#define CACHE_MAGIC                 0x46545243 /* 'FTRC' */
#define REG_VCOUNT                  (*(volatile u16 *)0x04000006)

typedef struct {
    u16 model_id;       /* 0xFFFF when unoccupied */
    u8  arena;          /* arena holding the texture */
    u8  dist;           /* tile distance to the player when last drawn */
    u16 tex_off;        /* offset inside the arena */
    u16 tex_size;       /* bytes used inside the arena (TEX_ALIGN multiple) */
    u32 last_used_tick; /* monotonic access counter for LRU eviction */
    u32 last_frame_seq; /* frame_seq when drawn, so slots drawn this frame are not evicted */
    void *arc_buf;      /* decompressed NARC buffer on root_heap */
    void *mdl_ptr;      /* NNSG3dResMdl* inside arc_buf */
    u32 vram_slot[5];   /* 0x14-byte VRAM key set (vtable, tex, tex4x4, pltt, flag) */
    u32 mdl_obj[39];    /* 0x9C-byte AC:WW render model wrapper */
} OutdoorFtrSlot;

typedef struct {
    u32 magic;
    u32 tick_counter;
    u32 last_raw_tag;
    u32 frame_seq;
    u32 owner_ctx;      /* ov003 context that created this cache */
    u32 heap_free_seen; /* debug: largest free block at the last load attempt */
    u32 fail_count;     /* debug: loads refused (VRAM / heap / file) */
    u32 retry_seq;      /* no load attempts before this frame_seq (scene settle delay) */
    u32 neg_model;      /* model whose load was refused last, and the frame_seq until it is not retried */
    u32 neg_seq;
    u32 arena_key[NUM_ARENAS];  /* NNS tex keys of the claimed texture arenas (0 = none) */
    u32 arena_size[NUM_ARENAS];
    u32 pltt_key;       /* NNS pltt key: MAX_FTR_SLOTS * PLTT_SLOT_SIZE bytes, slot i owns part i */
    u32 vram_claimed;   /* 1 once claiming was attempted */
    int player_gx;      /* player tile in grid coordinates (see grid_coords), this frame */
    int player_gz;
    OutdoorFtrSlot slots[MAX_FTR_SLOTS];
} OutdoorFtrCache;

static OutdoorFtrCache *s_cache;
static u16 s_dropping_item; /* furniture id being dropped from the pockets (0 = none) */
u32 g_ftr_dbg[4];           /* debug counters: shape calls, furniture hits, markers written, markers cleared */

/* Collision cylinder for outdoor furniture: radius=0x0C, height=0x10, kind=0x06 */
static const u8 s_furniture_shape[4] = { 0x0C, 0x10, 0x06, 0x00 };

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

/* True when a neighbouring multi-square furniture piece covers (ux, uz). */
static int covered_by_neighbour(int ux, int uz) {
    int dx, dz;
    for (dz = -1; dz <= 1; dz++) {
        for (dx = -1; dx <= 1; dx++) {
            u16 *t;
            u32 fp[2];
            u32 n, i;
            if (dx == 0 && dz == 0) {
                continue;
            }
            t = town_tile(ux + dx, uz + dz);
            if (t == 0 || !is_furniture_item(*t)) {
                continue;
            }
            n = footprint_init(fp, t);
            for (i = 1; i < n; i++) {
                const s16 *sq = FN_FTPRINT_SQUARE(fp, i);
                if (dx + sq[0] == 0 && dz + sq[1] == 0) {
                    return 1;
                }
            }
        }
    }
    return 0;
}

/* ------------------------------------------------------------------------- */
/* Model cache                                                                */
/* ------------------------------------------------------------------------- */

static void format_ftr_path(char *out, u32 model_id, int is_arc) {
    /* Formats "/ftr/%d/%d/%04x.arc" or "/ftr/%d/%d/%04x.nsbtx" without sprintf overhead */
    static const char hex[16] = {
        '0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'
    };
    u32 dir1 = model_id >> 8;
    u32 dir2 = (model_id >> 4) & 0xF;
    int p = 0;
    out[p++] = '/';
    out[p++] = 'f';
    out[p++] = 't';
    out[p++] = 'r';
    out[p++] = '/';
    out[p++] = (char)('0' + dir1);
    out[p++] = '/';
    if (dir2 >= 10) {
        out[p++] = '1';
        out[p++] = (char)('0' + (dir2 - 10));
    } else {
        out[p++] = (char)('0' + dir2);
    }
    out[p++] = '/';
    out[p++] = hex[(model_id >> 12) & 0xF];
    out[p++] = hex[(model_id >> 8) & 0xF];
    out[p++] = hex[(model_id >> 4) & 0xF];
    out[p++] = hex[model_id & 0xF];
    out[p++] = '.';
    if (is_arc) {
        out[p++] = 'a';
        out[p++] = 'r';
        out[p++] = 'c';
    } else {
        out[p++] = 'n';
        out[p++] = 's';
        out[p++] = 'b';
        out[p++] = 't';
        out[p++] = 'x';
    }
    out[p] = '\0';
}

/* Free bytes of the largest frame-VRAM texture region. */
static u32 vram_largest_free(void) {
    u32 best = 0;
    int i;
    for (i = 0; i < 4; i++) {
        u32 f = VRAM_TEX_HI_ADDR[i] - VRAM_TEX_LO_ADDR[i];
        if (f > best) {
            best = f;
        }
    }
    return best;
}

/* Claims texture arenas from the largest free regions (each keeps VRAM_TEX_RESERVE free) and one
 * palette block shared by all slots. Done once per scene, after the scene finished loading. */
static void claim_vram(OutdoorFtrCache *c) {
    u32 keys[5];
    int i;
    c->vram_claimed = 1;
    if (*VRAM_PAL_END_ADDR - *VRAM_PAL_CUR_ADDR < MAX_FTR_SLOTS * PLTT_SLOT_SIZE + VRAM_PLTT_RESERVE) {
        return;
    }
    FN_VRAM_SLOT_INIT(keys);
    FN_VRAM_SLOT_ALLOC(keys, 0, 0, MAX_FTR_SLOTS * PLTT_SLOT_SIZE);
    if (keys[3] == 0) {
        return;
    }
    c->pltt_key = keys[3];
    for (i = 0; i < NUM_ARENAS; i++) {
        u32 f = vram_largest_free();
        u32 sz;
        if (f < MIN_ARENA_SIZE + VRAM_TEX_RESERVE) {
            break;
        }
        sz = (f - VRAM_TEX_RESERVE) & ~(TEX_ALIGN - 1);
        if (sz > MAX_ARENA_SIZE) {
            sz = MAX_ARENA_SIZE;
        }
        FN_VRAM_SLOT_INIT(keys);
        FN_VRAM_SLOT_ALLOC(keys, sz, 0, 0);
        if (keys[1] == 0) {
            break;
        }
        c->arena_key[i] = keys[1];
        c->arena_size[i] = sz;
    }
}

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
    if (slot->arc_buf != 0) {
        FN_HEAP_FREE(root_heap, slot->arc_buf);
    }
    slot->arc_buf = 0;
    slot->mdl_ptr = 0;
    slot->model_id = 0xFFFF;
}

/* First-fit search for size bytes in arena a; returns the offset or -1. */
static int arena_find_gap(OutdoorFtrCache *c, int a, u32 size) {
    u32 pos = 0;
    for (;;) {
        int i;
        int moved = 0;
        if (pos + size > c->arena_size[a]) {
            return -1;
        }
        for (i = 0; i < MAX_FTR_SLOTS; i++) {
            OutdoorFtrSlot *s = &c->slots[i];
            if (s->model_id != 0xFFFF && s->arena == a &&
                s->tex_off < pos + size && pos < (u32)s->tex_off + s->tex_size) {
                pos = (u32)s->tex_off + s->tex_size;
                moved = 1;
            }
        }
        if (!moved) {
            return (int)pos;
        }
    }
}

/* Slot that may be evicted for a request at tile distance dist, or -1. */
static int find_victim(OutdoorFtrCache *c, u32 dist) {
    int i;
    int victim = -1;
    u32 best_tick = 0xFFFFFFFF;
    u32 far = dist + 2;
    for (i = 0; i < MAX_FTR_SLOTS; i++) {
        OutdoorFtrSlot *s = &c->slots[i];
        if (s->model_id != 0xFFFF && s->last_frame_seq != c->frame_seq && s->last_used_tick < best_tick) {
            best_tick = s->last_used_tick;
            victim = i;
        }
    }
    if (victim >= 0) {
        return victim;
    }
    /* Everything was drawn this frame: a clearly farther model gives way to a nearer one */
    for (i = 0; i < MAX_FTR_SLOTS; i++) {
        OutdoorFtrSlot *s = &c->slots[i];
        if (s->model_id != 0xFFFF && s->dist > far) {
            far = s->dist;
            victim = i;
        }
    }
    return victim;
}

/* Cheap pre-check (no file access): can a texture of up to 0x2000 bytes be placed right now? */
static int can_place(OutdoorFtrCache *c, u32 dist) {
    int i;
    for (i = 0; i < MAX_FTR_SLOTS; i++) {
        if (c->slots[i].model_id == 0xFFFF) {
            int a;
            for (a = 0; a < NUM_ARENAS; a++) {
                if (c->arena_key[a] != 0 && arena_find_gap(c, a, 0x2000) >= 0) {
                    return 1;
                }
            }
            break;
        }
    }
    return find_victim(c, dist) >= 0;
}

/* Finds a free slot plus arena space for a texture of tex_sz bytes, evicting least recently used models
 * that were not drawn this frame. Returns the slot index (arena/tex_off/tex_size filled) or -1. */
static int pick_slot(OutdoorFtrCache *c, u32 tex_sz, u32 root_heap, u32 dist) {
    u32 size = (tex_sz + TEX_ALIGN - 1) & ~(TEX_ALIGN - 1);
    for (;;) {
        int i;
        int free_slot = -1;
        int victim;
        for (i = 0; i < MAX_FTR_SLOTS; i++) {
            if (c->slots[i].model_id == 0xFFFF) {
                free_slot = i;
                break;
            }
        }
        if (free_slot >= 0) {
            int a;
            for (a = 0; a < NUM_ARENAS; a++) {
                int off;
                if (c->arena_key[a] == 0) {
                    continue;
                }
                off = arena_find_gap(c, a, size);
                if (off >= 0) {
                    OutdoorFtrSlot *s = &c->slots[free_slot];
                    s->arena = (u8)a;
                    s->tex_off = (u16)off;
                    s->tex_size = (u16)size;
                    return free_slot;
                }
            }
        }
        victim = find_victim(c, dist);
        if (victim < 0) {
            return -1;
        }
        slot_release_model(&c->slots[victim], root_heap);
    }
}

/* Waits for the start of VBlank, when the 3D engine is not reading texture VRAM. */
static void wait_vblank_window(void) {
    u32 guard = 0;
    while (guard++ < 0x80000) {
        u16 v = REG_VCOUNT;
        if (v >= 192 && v < 202) {
            return;
        }
    }
}

/* Loads model_id into a slot. Returns the slot index or -1. */
static int load_model(OutdoorFtrCache *c, u16 model_id, u32 root_heap, u32 dist) {
    static const char s_arc_name[4] = { 'F', 'T', 'R', '\0' };
    static const char s_bmd_path[16] = "FTR:a/bmd/bmd0";
    char path_buf[32];
    u32 file_sz = 0;
    void *btx_buf;
    void *arc_buf;
    void *bmd_file;
    void *tex_res;
    u8 *mdl_set;
    void *mdl_ptr;
    u32 tex_sz;
    int idx;
    OutdoorFtrSlot *slot;
    u32 archive_words[27]; /* 108 bytes, 4-byte aligned for NNSFndArchive */

    c->heap_free_seen = FN_HEAP_ALLOCATABLE(root_heap, 4);
    if (c->heap_free_seen < HEAP_MIN_FREE) {
        return -1;
    }

    format_ftr_path(path_buf, model_id, 0);
    btx_buf = FN_FS_LOAD_DECOMPRESS(path_buf, root_heap, -4, &file_sz);
    if (btx_buf == 0) {
        return -1;
    }
    tex_res = FN_NNS_G3D_GET_TEX(btx_buf);
    if (tex_res == 0 || FN_NNS_G3D_TEX4X4_REQ_SIZE(tex_res) != 0 ||
        FN_NNS_G3D_PLTT_REQ_SIZE(tex_res) > PLTT_SLOT_SIZE) {
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }
    tex_sz = FN_NNS_G3D_TEX_REQ_SIZE(tex_res);
    idx = pick_slot(c, tex_sz, root_heap, dist);
    if (idx < 0) {
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }
    slot = &c->slots[idx];

    format_ftr_path(path_buf, model_id, 1);
    arc_buf = FN_FS_LOAD_DECOMPRESS(path_buf, root_heap, 4, &file_sz);
    if (arc_buf == 0) {
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }

    if (!FN_NNS_FND_MOUNT_ARCHIVE(archive_words, s_arc_name, arc_buf)) {
        FN_HEAP_FREE(root_heap, arc_buf);
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }
    bmd_file = FN_NNS_FND_GET_ARC_FILE(s_bmd_path);
    FN_NNS_FND_UNMOUNT_ARCHIVE(archive_words);
    if (bmd_file == 0) {
        FN_HEAP_FREE(root_heap, arc_buf);
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }

    mdl_set = FN_NNS_G3D_GET_MDL_SET(bmd_file);
    mdl_ptr = (void *)(mdl_set + *(u32 *)(mdl_set + *(u16 *)(mdl_set + 0x0E) + 0x0C));

    /* Point the slot's key set at its arena piece and its palette part, then upload during VBlank */
    FN_VRAM_SLOT_INIT(slot->vram_slot);
    slot->vram_slot[1] = c->arena_key[slot->arena] + (slot->tex_off >> 3);
    slot->vram_slot[2] = 0;
    slot->vram_slot[3] = c->pltt_key + (u32)idx * (PLTT_SLOT_SIZE >> 3);
    wait_vblank_window();
    FN_TEX_UPLOAD_TO_SLOT(tex_res, slot->vram_slot);
    FN_MDL_OBJ_INIT(slot->mdl_obj);
    FN_MODEL_BIND(slot->mdl_obj, mdl_ptr, tex_res);
    slot->mdl_obj[0x60 / 4] = 0;

    /* The texture image and palette now live in VRAM; the .nsbtx buffer is no longer needed */
    FN_HEAP_FREE(root_heap, btx_buf);

    slot->arc_buf = arc_buf;
    slot->mdl_ptr = mdl_ptr;
    slot->model_id = model_id;
    slot->dist = (u8)dist;
    slot->last_frame_seq = 0;
    return idx;
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

    if (root_heap == 0) {
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
            claim_vram(cache);
        }
        if (model_id == cache->neg_model && cache->frame_seq < cache->neg_seq) {
            return 0;
        }
        if (!can_place(cache, dist)) {
            return 0;
        }
        slot_idx = load_model(cache, model_id, root_heap, dist);
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

    emi = FN_LIGHT_SLOT2_TO_EMI();
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
        if (draw_outdoor_furniture(ctx, item_ptr, mtx_src)) {
            return;
        }
    }

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
    if (is_furniture_item(item)) {
        g_ftr_dbg[1]++;
        ensure_markers(item_ptr, ux, uz);
        shape = s_furniture_shape;
    } else if (item == ITEM_EMPTY) {
        /* A secondary square can be queried before its anchor: mark it as soon as it is seen */
        if (!covered_by_neighbour(ux, uz)) {
            return 0;
        }
        *item_ptr = ITEM_FTR_COVERED;
        g_ftr_dbg[2]++;
        shape = s_furniture_shape;
    } else if (item == ITEM_FTR_COVERED) {
        if (!covered_by_neighbour(ux, uz)) {
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
