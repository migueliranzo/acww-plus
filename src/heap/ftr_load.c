/*
 * AC:WW+ heap code (code home, see src/code_home.c): outdoor furniture model loading.
 * Linked at 0 and relocated by the loader into a root-heap block; it only calls the game and the ITCM payload
 * through absolute pointers. Exports are listed in tools/build_rom.py (HX_EXPORTS), in code_home.h order.
 */

#include "ftr_shared.h"

extern u32 g_ftr_perf[4];

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
void hx_claim_vram(OutdoorFtrCache *c) {
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
        /* Not drawn this frame nor the last one: really out of view. (Only "not drawn this frame" would also
         * match models the draw loop has simply not reached yet, and thrash: ~4 reloads per frame.) */
        if (s->model_id != 0xFFFF && s->last_frame_seq + 1 < c->frame_seq && s->last_used_tick < best_tick) {
            best_tick = s->last_used_tick;
            victim = i;
        }
    }
    if (victim >= 0) {
        return victim;
    }
    /* Everything is in view: a clearly farther model gives way to a nearer one */
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
int hx_can_place(OutdoorFtrCache *c, u32 dist) {
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
        g_ftr_perf[1]++;
        slot_release_model(&c->slots[victim], root_heap);
    }
}

#ifndef FTR_HALF_RES
#define FTR_HALF_RES 1
#endif

#if FTR_HALF_RES
/*
 * Halves every texture of a TEX0 resource (2x nearest-neighbour, minimum 8 texels) and packs the texel data,
 * so the model needs a quarter of the texture VRAM. The dictionary keeps the halved size in the TEXIMAGE param
 * and in extraParam (orig width / height), which the model binding compares with the material's own size
 * (origWidth / magW) to scale the texture coordinates.
 */
static void tex_halve(u8 *tex) {
    u8 *dict = tex + *(u16 *)(tex + 0x0E);
    u32 count = dict[1];
    u8 *info = dict + *(u16 *)(dict + 6);
    u32 esz = *(u16 *)info;
    u8 *data = tex + *(u32 *)(tex + 0x14);
    u32 wpos = 0;
    u32 last = 0;
    u32 done;
    for (done = 0; done < count; done++) {
        /* next texture in data order (texels are packed front to back, so reads stay ahead of writes) */
        u32 i, best = 0xFFFFFFFF, bi = 0;
        u32 *ent;
        u32 p, off, ws, hs, fmt, bpp, w, h, nw, nh, x, y;
        for (i = 0; i < count; i++) {
            u32 o = (*(u32 *)(info + 4 + i * esz) & 0xFFFF) << 3;
            if ((done == 0 || o > last) && o < best) {
                best = o;
                bi = i;
            }
        }
        if (best == 0xFFFFFFFF) {
            break;
        }
        last = best;
        ent = (u32 *)(info + 4 + bi * esz);
        p = ent[0];
        off = (p & 0xFFFF) << 3;
        ws = (p >> 20) & 7;
        hs = (p >> 23) & 7;
        fmt = (p >> 26) & 7;
        bpp = fmt == 2 ? 2 : fmt == 3 ? 4 : (fmt == 1 || fmt == 4 || fmt == 6) ? 8 : 0;
        w = 8u << ws;
        h = 8u << hs;
        if (bpp == 0 || (ws == 0 && hs == 0)) {
            /* format kept as is: move it down unchanged */
            u32 n = (w * h * (fmt == 7 ? 16 : 8)) >> 3, k;
            if (fmt == 5) {
                n = (w * h) >> 2;
            }
            for (k = 0; k < n; k++) {
                data[wpos + k] = data[off + k];
            }
            ent[0] = (p & ~0xFFFF) | (wpos >> 3);
            wpos += n;
            continue;
        }
        nw = ws ? w >> 1 : w;
        nh = hs ? h >> 1 : h;
        for (y = 0; y < nh; y++) {
            for (x = 0; x < nw; x++) {
                u32 sx = ws ? x << 1 : x, sy = hs ? y << 1 : y;
                u32 si = sy * w + sx, di = y * nw + x;
                u32 v;
                if (bpp == 8) {
                    data[wpos + di] = data[off + si];
                    continue;
                }
                if (bpp == 4) {
                    v = (data[off + (si >> 1)] >> ((si & 1) << 2)) & 0xF;
                    data[wpos + (di >> 1)] = (u8)((data[wpos + (di >> 1)] & ~(0xF << ((di & 1) << 2))) | (v << ((di & 1) << 2)));
                } else {
                    v = (data[off + (si >> 2)] >> ((si & 3) << 1)) & 3;
                    data[wpos + (di >> 2)] = (u8)((data[wpos + (di >> 2)] & ~(3 << ((di & 3) << 1))) | (v << ((di & 3) << 1)));
                }
            }
        }
        ent[0] = (p & ~(0xFFFF | (7u << 20) | (7u << 23))) | (wpos >> 3) | ((ws ? ws - 1 : 0) << 20) | ((hs ? hs - 1 : 0) << 23);
        ent[1] = (ent[1] & ~0x3FFFFF) | nw | (nh << 11);
        wpos += (nw * nh * bpp) >> 3;
        wpos = (wpos + 7) & ~7u;
    }
    *(u16 *)(tex + 0x0C) = (u16)(wpos >> 3);   /* sizeTex: what NNS_G3dTexGetRequiredSize reports and uploads */
}

/*
 * After binding, materials whose texture is now smaller than authored have magW / magH != 1.0, but their texture
 * coordinates are only scaled through the texture matrix: turn it on (TEXMTX_USE, texgen = texcoord source).
 */
static void mdl_enable_tex_mag(u8 *mdl) {
    u8 *resmat = mdl + *(u32 *)(mdl + 8);
    u8 *dict = resmat + 4;
    u32 count = dict[1];
    u8 *info = dict + *(u16 *)(dict + 6);
    u32 esz = *(u16 *)info;
    u32 i;
    for (i = 0; i < count; i++) {
        u8 *md = resmat + *(u32 *)(info + 4 + i * esz);
        if (*(s32 *)(md + 0x24) != 0x1000 || *(s32 *)(md + 0x28) != 0x1000) {
            *(u16 *)(md + 0x1E) |= 0x0001;         /* NNS_G3D_MATFLAG_TEXMTX_USE */
            *(u32 *)(md + 0x14) |= 1u << 30;       /* TEXIMAGE texgen: texcoord source (uses the texture matrix) */
            *(u32 *)(md + 0x18) |= 3u << 30;
        }
    }
}
#endif

/* Loads model_id into a slot. Returns the slot index or -1. */
int hx_load_model(OutdoorFtrCache *c, u16 model_id, u32 root_heap, u32 dist) {
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
#if FTR_HALF_RES
    tex_halve((u8 *)tex_res);
#endif
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

    /* Point the slot's key set at its arena piece and its palette part. The copy itself goes through the game's
     * VBlank request queue (cache flush + NNS_G3dTexLoad/PlttLoad in its VBlank window), like the player's body
     * textures: a direct upload from the draw loop raced the game's own VRAM transfers on hardware. */
    FN_VRAM_SLOT_INIT(slot->vram_slot);
    slot->vram_slot[1] = c->arena_key[slot->arena] + (slot->tex_off >> 3);
    slot->vram_slot[2] = 0;
    slot->vram_slot[3] = c->pltt_key + (u32)idx * (PLTT_SLOT_SIZE >> 3);
    FN_VRAMKEYS_APPLY(slot->vram_slot, tex_res);
    FN_MDL_OBJ_INIT(slot->mdl_obj);
    FN_MODEL_BIND(slot->mdl_obj, mdl_ptr, tex_res);
#if FTR_HALF_RES
    mdl_enable_tex_mag((u8 *)mdl_ptr);
#endif
    slot->mdl_obj[0x60 / 4] = 0;

    if (!FN_VRAM_REQ_SUBMIT_TEXLOAD(slot->req, tex_res, 1)) {
        FN_HEAP_FREE(root_heap, arc_buf);
        FN_HEAP_FREE(root_heap, btx_buf);
        return -1;
    }
    slot->btx_buf = btx_buf;
    slot->arc_buf = arc_buf;
    slot->mdl_ptr = mdl_ptr;
    g_ftr_perf[0]++;
    slot->model_id = model_id;
    slot->dist = (u8)dist;
    slot->last_frame_seq = 0;
    return idx;
}

