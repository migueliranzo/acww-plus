/*
 * AC:WW+ outdoor furniture: engine addresses, budgets and the model cache layout, shared by the ITCM part
 * (src/outdoor_furniture.c) and the heap-loaded part (src/heap/ftr_load.c).
 */
#ifndef FTR_SHARED_H
#define FTR_SHARED_H

#include "acww.h"

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
#define FN_FIELD_ITEM_PUT_REQ      ((u32 (*)(u32 player, int *unit_xz, u32 item, u32 expect, u32 a5, u32 a6, u32 a7, u32 a8, u32 a9, int a10))(0x020457B4 | 1))
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
#define FN_VRAMKEYS_APPLY           ((void (*)(void *vram_slot, void *tex_res))(0x0205540C | 1))
#define FN_VRAM_REQ_CANCEL          ((void (*)(void *req))(0x020B8E9C | 1))
#define FN_VRAM_REQ_SUBMIT_TEXLOAD  ((int (*)(void *req, void *tex_res, int flag))(0x020B8EC4 | 1))
#define FN_VRAM_REQ_CTOR            ((void *(*)(void *req))(0x020B8FF4 | 1))
#define FN_FS_LOAD_DECOMPRESS       ((void *(*)(const char *path, u32 heap, int align, u32 *out_sz))(0x02064490 | 1))
#define FN_LIGHT_SLOT2_TO_EMI       ((u16 (*)(void))(0x02064F68 | 1))
#define FN_OTHER_PLAYERS_COUNT      ((u32 (*)(void))(0x020B13A8 | 1))
#define FN_OV003_ACT_ON_TARGET      ((int (*)(u32 actor))(0x022085DC | 1))
#define FN_OV003_SHAPE_LOOKUP_ORIG  ((const u8 *(*)(const u16 *item_ptr))(0x022235BC | 1))

/* Global Engine Addresses */
#define REG_KEYINPUT                ((volatile u16 *)0x04000130)  /* active low, bit 0 = A */
#define PLAYER_IDX_PTR              0x020CC0C8   /* -> +0x68 local player index */
#define PLAYER_REC_BASE             0x021DAA04   /* save RAM + 0xC: player records */
#define PLAYER_REC_SIZE             0x228C
#define PLAYER_REC_HAND             0x220A       /* u16 held item, 0xFFF1 = empty */
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
#define ITEM_FTR_COVERED            0xF031

/* Budgets */
#define MAX_FTR_SLOTS               24
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
#define REQ_PENDING(s)              (((u8 *)(s)->req)[0xD] == 1) /* queued, not yet copied to VRAM */

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
    void *btx_buf;      /* .nsbtx buffer, kept until the queued upload ran */
    u32 req[7];         /* 0x1C-byte VBlank VRAM request (the game's own texture upload queue) */
} OutdoorFtrSlot;

typedef struct {
    u32 magic;
    u32 tick_counter;
    u32 last_raw_tag;
    u32 frame_seq;
    u32 owner_ctx;      /* ov003 context that created this cache */
    u32 heap_free_seen; /* debug: largest free block at the last load attempt */
    u32 fail_count;     /* debug: loads refused (VRAM / heap / file) */
    u32 retry_seq;      /* no load attempts before this frame_seq (scene settle delay, one load per frame) */
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


#endif
