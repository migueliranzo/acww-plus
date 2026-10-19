/*
 * AC:WW+ Skin tone on the bedroom phone (Service Center).
 *
 * The upstairs phone's Service Center menu gets a "Change my look." entry (select2 #22). It opens message 0x43
 * of sequence1_ ("What would you like to change?" Skin tone / Shoes / Socks / That's all):
 *   0x44 skin question (Lighter / Darker / This is fine) -> 0x45 / 0x46 step the tone, back to 0x44
 *   0x47 / 0x48 step the shoe / sock colour (src/body_colors.c), back to 0x43
 *
 * Skin tone = the tan level (player +0x223D bits 3-5, 8 skin palettes: PPal = 8 x face + tan).
 * The chosen tone is kept as a per-player base in the never-written save word PostOffice pad_98e
 * (block 0x14FCA, 4 bits per player: base + 1, 0 = not set, so vanilla saves behave as before).
 * Tan fading (player_tan_level: -days/2 since the last sun) never goes below the base; summer tanning
 * still darkens it and fades back to the base.
 */
#include "acww.h"

#define FN_TAN_SET                  ((void (*)(u8 *rec, u32 tan))(0x02098B1C | 1))
#define FN_PLAYER_RECORD            ((u8 *(*)(u32 actor))(0x02010DF4 | 1))
#define FN_PLAYER_TAN_LEVEL         ((u32 (*)(u32 actor, int write))(0x02010BDC | 1))
#define FN_PLAYER_HEAD_REQUEST      ((int (*)(u32 actor, u16 *hat, u32 c96, u32 c97, u32 c98))(0x0200FB8C | 1))
#define ACTOR_HEAD_HAT              0xC94    /* head rebuild request: state +0xC90 (2 = idle), hat, c96..c98 */
#define FN_PHONE_MSG_OPEN_ORIG      ((void (*)(u32 obj))(0x0222D544 | 1))   /* ov004 */

#define PLAYER_RECORDS              0x021DAA04   /* block 0xC */
#define PLAYER_ACTORS               ((volatile u32 *)0x021D3F04)  /* 4 slots (player_actor_get) */
#define PLAYER_RECORD_SIZE          0x228C
#define SKIN_BASE_WORD              (*(volatile u16 *)0x021EF9C2)   /* block 0x14FCA */
#define PREC_HAIR_TAN               0x223D

#define PHONE_MSG                   0x2AE    /* u8: current message of the phone talk */
#define MSG_LOOK_MENU               0x43
#define MSG_SKIN_ASK                0x44
#define MSG_SKIN_LIGHTER            0x45
#define MSG_SKIN_DARKER             0x46
#define MSG_SHOES                   0x47
#define MSG_SOCKS                   0x48

/* Service Center menus of the upstairs phone, replacing ov004 0x02251978 / 0x02243978 (scene 6, waking up:
 * with the clock) and 0x02251980 / 0x02243974 (walked upstairs). Entries are select2 ids. */
static const u8 s_phone_choices[5] = { 0x07, 0x08, 0x16, 0x11, 0x17 }; /* clock, sound, my look, downloads, nothing */
static const u8 s_phone_choices_awake[4] = { 0x08, 0x16, 0x11, 0x17 };  /* sound, my look, downloads, nothing */
const u32 g_phone_choice_list[2] = { (u32)s_phone_choices, 5 };
const u32 g_phone_choice_list_awake[2] = { (u32)s_phone_choices_awake, 4 };
const u8 g_phone_next_msg[8] = { 0x0F, 0x1B, MSG_LOOK_MENU, 0x17, 0x20, 0, 0, 0 };
const u8 g_phone_next_msg_awake[4] = { 0x1B, MSG_LOOK_MENU, 0x17, 0x20 };

static u8 s_last_msg = 0xFF;

static int record_index(const u8 *rec) {
    int i;
    for (i = 0; i < 4; i++) {
        if (rec == (const u8 *)(PLAYER_RECORDS + i * PLAYER_RECORD_SIZE)) {
            return i;
        }
    }
    return -1;
}

/* Base tone of player i, or -1 when none was chosen. */
static int skin_base(int i) {
    int v;
    if (i < 0) {
        return -1;
    }
    v = (SKIN_BASE_WORD >> (i * 4)) & 0xF;
    return v == 0 ? -1 : v - 1;
}

static void skin_base_set(int i, int tone) {
    u16 w = SKIN_BASE_WORD;
    w &= ~(0xF << (i * 4));
    w |= (u16)((tone + 1) << (i * 4));
    SKIN_BASE_WORD = w;
}

/* The player on the phone: the current one, or (wake-up screen, no player current yet) the one in bed. */
static u32 phone_player(u8 **rec_out) {
    u32 actor = FN_GET_PLAYER_ACTOR(4);
    int i;
    if (actor == 0) {
        for (i = 0; i < 4 && actor == 0; i++) {
            actor = PLAYER_ACTORS[i];
        }
    }
    *rec_out = actor != 0 ? FN_PLAYER_RECORD(actor) : FN_PLAYER_RECORD_CURRENT();
    return actor;
}

/* what: 0 lighter, 1 darker, 2 next shoe colour, 3 next sock colour */
static void look_change(int what) {
    u8 *rec;
    u32 actor = phone_player(&rec);
    int i = record_index(rec);
    int tone;
    if (rec == 0 || i < 0) {
        return;
    }
    tone = (rec[PREC_HAIR_TAN] >> 3) & 7;
    if (what <= 1) {
        tone += what == 0 ? -1 : 1;
        if (tone < 0) {
            tone = 0;
        }
        if (tone > 7) {
            tone = 7;
        }
        skin_base_set(i, tone);
        FN_TAN_SET(rec, (u32)tone);
    } else {
        body_colors_step(rec, what - 2);
    }
    if (actor != 0) {
        /* Head: rebuild with its current parts (copies the skin palette); body: palettes + VBlank upload */
        u16 hat = *(u16 *)(actor + ACTOR_HEAD_HAT);
        if (what <= 1) {
            FN_PLAYER_HEAD_REQUEST(actor, &hat, *(u8 *)(actor + ACTOR_HEAD_HAT + 2),
                                   *(u8 *)(actor + ACTOR_HEAD_HAT + 3), *(u8 *)(actor + ACTOR_HEAD_HAT + 4));
        }
        body_colors_refresh(actor, (u32)tone);
    }
}

/*
 * Hook: the phone talk's message-open callback (ov004 vtable entry 0x02251A04, func_ov004_0222d544).
 * Applies the change when a reply of the look menu opens.
 */
void hook_phone_msg_open(u32 obj) {
    u8 msg;
    FN_PHONE_MSG_OPEN_ORIG(obj);
    msg = *(u8 *)(obj + PHONE_MSG);
    if (msg != s_last_msg) {
        if (msg == MSG_SKIN_LIGHTER) {
            look_change(0);
        } else if (msg == MSG_SKIN_DARKER) {
            look_change(1);
        } else if (msg == MSG_SHOES) {
            look_change(2);
        } else if (msg == MSG_SOCKS) {
            look_change(3);
        }
    }
    s_last_msg = msg;
}

/*
 * Hook: the two calls of player_tan_level (actor init 0x0200DF00, player_setup 0x0200FC6E).
 * The faded tan never goes below the chosen base tone.
 */
u32 hook_player_tan_level(u32 actor, int write) {
    u32 tan = FN_PLAYER_TAN_LEVEL(actor, write);
    u8 *rec = FN_PLAYER_RECORD(actor);
    int base;
    if (rec == 0) {
        return tan;
    }
    base = skin_base(record_index(rec));
    if (base >= 0 && tan < (u32)base) {
        tan = (u32)base;
        if (write) {
            FN_TAN_SET(rec, tan);
        }
    }
    return tan;
}
