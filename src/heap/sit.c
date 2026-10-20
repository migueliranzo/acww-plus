/*
 * AC:WW+ code home: sitting on outdoor chairs, benches and sofas.
 *
 * Indoors, sitting is the ov004 player actions 0x25 (sit down), 0x28 (sitting) and 0x2C (stand up). ov004 isn't
 * loaded in town, so the build points those actions' table entries at ITCM trampolines (src/outdoor_furniture.c):
 * indoors they call the ov004 handlers, outdoors these simplified versions. The trigger is A with empty hands,
 * facing a seat (see ftr_sit_use in src/outdoor_furniture.c).
 *
 * Sit down: the player moves onto the seat square's centre, turns the way the piece faces, plays ft_sitdown1.
 * Sitting: ft_sitdown_wait1 loops until the d-pad or B is pressed. Stand up: ft_standup1, then the player is put
 * back where they stood before sitting, and the action ends like the indoor one (end priority + stand request).
 * The steps are timed (20 logic frames each): the animation clock never reports "ended" for these animations in
 * town. pad_stick_magnitude() was not usable either (it ended the sitting at once), so keys are read from KEYINPUT.
 */

#include "ftr_shared.h"

#define FN_PLAYER_REQ_QUEUE     ((int (*)(u32 actor, void *req))(0x0200E31C | 1))
#define FN_PLAYER_SET_ANIM_B    ((void (*)(u32 actor, int anim, int a, int b))(0x0201042C | 1))
#define FN_PLAYER_ANIM_START    ((void (*)(u32 actor, int anim, int a, int b))(0x02010488 | 1))
#define FN_PLAYER_END_PRIORITY  ((u32 (*)(u32 actor, u32 cur))(0x02007CDC | 1))
#define FN_PLAYER_REQUEST_STAND ((void (*)(u32 actor, int a, int prio, int b))(0x0200CF6C | 1))
#define FN_PLAYER_SET_FACING    ((void (*)(u32 actor, const void *angle))(0x02010B2C | 1))

#define ACT_SIT_DOWN            0x25
#define ACT_SITTING             0x28
#define ACT_STAND_UP            0x2C
#define ANIM_SIT_DOWN           0x21
#define ANIM_SITTING            0x24
#define ANIM_STAND_UP           0x27
#define KEYS_STAND_UP           0x00F2   /* B and the d-pad (KEYINPUT bits, active low) */

/* Seat models: ftr_info dma.bin byte 2 (behaviour kind) 0x08, 0x09, 0x26 or 0x2C, the kinds the indoor chair class
 * (profile 0x36) handles. Same in every language file. */
static const u16 s_seat_models[59] = {
    0x003, 0x004, 0x00D, 0x00E, 0x00F, 0x017, 0x018, 0x021, 0x022, 0x02B, 0x02C, 0x035, 0x036, 0x03F, 0x040,
    0x049, 0x04A, 0x04B, 0x053, 0x054, 0x05D, 0x05E, 0x067, 0x068, 0x071, 0x072, 0x07B, 0x07C, 0x085, 0x086,
    0x0C4, 0x0D6, 0x0F4, 0x0F9, 0x0FC, 0x112, 0x113, 0x132, 0x133, 0x136, 0x137, 0x13C, 0x13D, 0x13F, 0x141,
    0x143, 0x16D, 0x1B9, 0x1BA, 0x1DC, 0x1DD, 0x1DE, 0x1DF, 0x1EC, 0x1F2, 0x1F8, 0x208, 0x696, 0x697
};

static s32 s_seat_x, s_seat_z;      /* fx32 seat position */
static s32 s_back_x, s_back_z;      /* where the player stood before sitting */
static s32 s_seat_angle;
static u32 s_ticks;                 /* logic frames in the current action */

int hx_is_seat_model(u32 model_id) {
    int i;
    for (i = 0; i < 59; i++) {
        if (s_seat_models[i] == model_id) {
            return 1;
        }
    }
    return 0;
}

static void queue_action(u32 p, u32 id) {
    u32 req[7];
    int i;
    for (i = 0; i < 7; i++) {
        req[i] = 0;
    }
    req[0] = id;
    req[1] = 6;                     /* priority, as the indoor requests */
    *(s16 *)&req[2] = -1;
    FN_PLAYER_REQ_QUEUE(p, req);
}

/* Sits the player on the square (ux, uz) of a seat facing `facing` (item & 3). */
int hx_sit_request(u32 p, int ux, int uz, u32 facing) {
    s_seat_x = (ux << 13) + 0x1000;
    s_seat_z = (uz << 13) + 0x1000;
    s_seat_angle = (s32)((facing & 3) << 14);
    queue_action(p, ACT_SIT_DOWN);
    return 1;
}

static void hold_seat(u32 p) {
    *(s32 *)(p + 0x5C) = s_seat_x;
    *(s32 *)(p + 0x64) = s_seat_z;
}

void hx_sit_start(u32 p, u32 req, u32 id) {
    s_ticks = 0;
    (void)req;
    if (id == ACT_SIT_DOWN) {
        s_back_x = *(s32 *)(p + 0x5C);
        s_back_z = *(s32 *)(p + 0x64);
        hold_seat(p);
        FN_PLAYER_SET_FACING(p, &s_seat_angle);
        FN_PLAYER_SET_ANIM_B(p, ANIM_SIT_DOWN, 3, 0);
    } else if (id == ACT_SITTING) {
        FN_PLAYER_ANIM_START(p, ANIM_SITTING, 0, 0);
    } else {
        FN_PLAYER_SET_ANIM_B(p, ANIM_STAND_UP, 0, 0);
    }
}

void hx_sit_tick(u32 p, u32 id) {
    s_ticks++;
    if (id == ACT_STAND_UP) {
        hold_seat(p);
        if (s_ticks > 20) {
            *(s32 *)(p + 0x5C) = s_back_x;
            *(s32 *)(p + 0x64) = s_back_z;
            *(u32 *)(p + 0x7F8) = FN_PLAYER_END_PRIORITY(p, *(u32 *)(p + 0x7EC));
            FN_PLAYER_REQUEST_STAND(p, 0, 1, -1);
        }
        return;
    }
    hold_seat(p);
    if (id == ACT_SIT_DOWN) {
        if (s_ticks > 20) {
            queue_action(p, ACT_SITTING);
        }
    } else if (s_ticks > 10 && (*REG_KEYINPUT & KEYS_STAND_UP) != KEYS_STAND_UP) {
        queue_action(p, ACT_STAND_UP);
    }
}
