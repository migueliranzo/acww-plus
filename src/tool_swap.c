/*
 * AC:WW+ Tool swap with the shoulder buttons.
 *
 * While the player stands with free field control (the moments when Y would open the pockets):
 *   R: equip the next tool from the pockets (the tool in hand takes its slot)
 *   L: put the tool in hand away into a free slot; with empty hands, take the last one back out
 * Holding L/R while walking still runs, as in vanilla (pad_to_player treats L/R like B): only a tap with no
 * direction or face button held counts. A tap during the equip animation is buffered for ~20 frames.
 * Equipping goes through player action 0x3F (func_02094ec4), the same request the pockets screen's doll uses,
 * so the animation, sounds and action priority rules are the game's own.
 */
#include "acww.h"

#define FN_STAND_TICK_ORIG          ((void (*)(u32, u32, u32, u32))(0x0200CC68 | 1))
#define FN_ACTION05_TICK_ORIG       ((void (*)(u32, u32, u32, u32))(0x0200C3D8 | 1))
#define FN_ACTION3F_TICK_ORIG       ((void (*)(u32, u32, u32, u32))(0x02009538 | 1))
#define FN_PLAYER_EQUIP_ITEM        ((int (*)(u16 *item))(0x02094EC4 | 1))   /* queues action 0x3F */
#define FN_PLAYER_REQUEST_STAND     ((int (*)(u32 actor, int pack, int prio, int arg))(0x0200CF6C | 1))
#define FN_MENU_IS_IDLE             ((int (*)(void))(0x0206F468 | 1))
#define FN_EVENT_CURRENT_EXISTS     ((int (*)(void))(0x0203E434 | 1))
#define FIELD_HUB_BLOCK             (*(volatile u32 *)0x021DA914)            /* hub refuses to open when != 0 */

#define TOOL_FIRST                  0x1369   /* shovel .. golden slingshot */
#define TOOL_LAST                   0x137B
#define TOY_FIRST                   0x13A0   /* held toys: vanish when unequipped in vanilla */
#define TOY_LAST                    0x13A7
#define BUFFER_TICKS                20

static u8 s_next_slot;              /* where R starts looking */
static s8 s_put_slot = -1;          /* slot of the tool L put away last */
static u8 s_field_equip;            /* 1 after an L/R equip until the player is back to standing */
static u16 s_buf_key;               /* buffered KEY_L / KEY_R tap */
static u8 s_buf_age;

static int is_tool(u16 item) {
    return item >= TOOL_FIRST && item <= TOOL_LAST;
}

static int is_toy(u16 item) {
    return item >= TOY_FIRST && item <= TOY_LAST;
}

static u32 slot_flags(u8 *rec, int slot) {
    return (*(u32 *)(rec + PREC_POCKET_FLAGS) >> (slot * 2)) & 3;
}

static void slot_flags_clear(u8 *rec, int slot) {
    *(u32 *)(rec + PREC_POCKET_FLAGS) &= ~(3u << (slot * 2));
}

/* Same conditions under which the hub opens the pockets from the field (menu_manager_tick). */
static int field_is_free(void) {
    return FIELD_CONTROL_STATE == 2 && FN_MENU_IS_IDLE() && FIELD_HUB_BLOCK == 0 && !FN_EVENT_CURRENT_EXISTS();
}

/* Remembers a lone L or R tap; called from every hooked tick of the local player. */
static void capture_tap(void) {
    u16 lr = PAD_PRESSED & (KEY_L | KEY_R);
    if (lr != 0 && lr != (KEY_L | KEY_R) &&
        (PAD_HELD & (KEY_DPAD | KEY_A | KEY_B | KEY_X | KEY_Y | KEY_START | KEY_SELECT)) == 0) {
        s_buf_key = lr;
        s_buf_age = 0;
    } else if (s_buf_key != 0 && ++s_buf_age > BUFFER_TICKS) {
        s_buf_key = 0;
    }
}

/* Equip pocket slot k (swapping the item in hand into it). Returns 1 when the game accepted the action. */
static int equip_from_slot(u8 *rec, int k) {
    u16 *pockets = (u16 *)(rec + PREC_POCKET_ITEMS);
    u16 *hand = (u16 *)(rec + PREC_HELD_ITEM);
    u16 item = pockets[k];
    u16 old = *hand;
    if (!FN_PLAYER_EQUIP_ITEM(&item)) {
        return 0;
    }
    s_field_equip = 1;
    pockets[k] = old;
    slot_flags_clear(rec, k);
    return 1;
}

static void do_swap(u16 key) {
    u8 *rec = FN_PLAYER_RECORD_CURRENT();
    u16 *pockets;
    u16 *hand;
    int i;

    if (rec == 0) {
        return;
    }
    pockets = (u16 *)(rec + PREC_POCKET_ITEMS);
    hand = (u16 *)(rec + PREC_HELD_ITEM);
    if (is_toy(*hand)) {
        return; /* putting a toy away would destroy it */
    }

    if (key == KEY_R) {
        /* Next tool in slot order, starting after the slot used last time */
        for (i = 0; i < POCKET_SLOTS; i++) {
            int k = s_next_slot + i;
            if (k >= POCKET_SLOTS) {
                k -= POCKET_SLOTS;
            }
            if (is_tool(pockets[k]) && slot_flags(rec, k) == 0) {
                if (equip_from_slot(rec, k)) {
                    s_next_slot = (u8)(k + 1 < POCKET_SLOTS ? k + 1 : 0);
                    s_put_slot = -1;
                }
                return;
            }
        }
        return;
    }

    /* L: put away */
    if (*hand != ITEM_EMPTY) {
        for (i = 0; i < POCKET_SLOTS; i++) {
            if (pockets[i] == ITEM_EMPTY) {
                u16 none = ITEM_EMPTY;
                u16 old = *hand;
                if (FN_PLAYER_EQUIP_ITEM(&none)) {
                    s_field_equip = 1;
                    pockets[i] = old;
                    slot_flags_clear(rec, i);
                    s_put_slot = (s8)i;
                }
                return;
            }
        }
        return; /* pockets full: keep it */
    }
    /* L with empty hands: take the last tool back out (else the first tool in the pockets) */
    if (s_put_slot >= 0 && is_tool(pockets[s_put_slot]) && slot_flags(rec, s_put_slot) == 0) {
        if (equip_from_slot(rec, s_put_slot)) {
            s_put_slot = -1;
        }
        return;
    }
    for (i = 0; i < POCKET_SLOTS; i++) {
        if (is_tool(pockets[i]) && slot_flags(rec, i) == 0) {
            equip_from_slot(rec, i);
            return;
        }
    }
}

/*
 * Hook: stand action tick (action 2; rodata member-function pair at 0x020D65A4, copied into the action tick
 * table 0x021C018C by func_02005368).
 */
void hook_player_stand_tick(u32 actor, u32 a1, u32 a2, u32 a3) {
    FN_STAND_TICK_ORIG(actor, a1, a2, a3);
    if (actor != FN_GET_PLAYER_ACTOR(4)) {
        return;
    }
    s_field_equip = 0; /* standing again (or never left) */
    capture_tap();
    if (s_buf_key != 0) {
        u16 key = s_buf_key;
        s_buf_key = 0;
        if (field_is_free()) {
            do_swap(key);
        }
    }
}

/*
 * Hook: action 5 tick (pair at 0x020D6804). Action 0x3F (equip) ends in action 5, the "item selected" pose that
 * the pockets screen keeps until it closes. After an L/R equip from the field there is no screen to close, so
 * the player is sent back to standing.
 */
void hook_player_action05_tick(u32 actor, u32 a1, u32 a2, u32 a3) {
    FN_ACTION05_TICK_ORIG(actor, a1, a2, a3);
    if (actor != FN_GET_PLAYER_ACTOR(4)) {
        return;
    }
    capture_tap();
    if (s_field_equip && FN_PLAYER_REQUEST_STAND(actor, 3, 5, -1)) {
        s_field_equip = 0;
    }
}

/* Hook: action 0x3F (equip animation) tick (pair at 0x020D6634): only buffers taps. */
void hook_player_action3f_tick(u32 actor, u32 a1, u32 a2, u32 a3) {
    FN_ACTION3F_TICK_ORIG(actor, a1, a2, a3);
    if (s_field_equip && actor == FN_GET_PLAYER_ACTOR(4)) {
        capture_tap();
    }
}
