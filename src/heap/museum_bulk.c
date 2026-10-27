/*
 * AC:WW+ code home: several items for Blathers in one go (donations and fossil assessments).
 *
 * Vanilla: "Donation!" / "Check a fossil!" open the plain slot picker (menu code 0x21, ov101) with a filter
 * (ov047_item_is_museum_related / ov047_item_is_unassessed_fossil). One item is shown, Blathers answers, then asks
 * "anything else?" and, on yes, opens the picker again.
 *
 * Here, while Blathers' picker is open, X marks the slot under the cursor (or unmarks it). A marked slot gets the
 * pocket grid's own green ring (ov094 draws it on slots whose mark bit is set). A picks a slot as usual (a marked
 * one too) and closes the picker. Blathers handles that item as in vanilla; whenever he would open the picker again,
 * the next marked slot is handed to him instead, as if it had been picked. A marked slot whose item changed since is skipped. Cancelling the picker drops the
 * marks; so does starting a new conversation with Blathers.
 */

#include "acww.h"

/* ov101: plain slot picker */
#define PK_CURSOR               0xB3            /* u8: 0..14 pocket slot, 15 quit button */
#define PK_MARK_BITS            (0xF4 + 0xA40)  /* ov094 grid model at +0xF4: slots drawn with the extra cell 0x02298648 */
#define FN_PICKER_GRID          ((void (*)(u8 *pk))(0x02299B54 | 1))           /* sub-state 6: d-pad on the grid */
#define FN_BITS_CLEAR           ((void (*)(void *bits, int i))(0x022969A4 | 1)) /* ov094 */
#define FN_BITS_SET             ((void (*)(void *bits, int i))(0x022969C4 | 1)) /* ov094 */

/* Menu IO block (main) */
#define MENU_CHOSEN_INDEX       (*(volatile u8 *)0x021CEB48)
#define MENU_CHOSEN_FLAG        (*(volatile u8 *)0x021CEB54)   /* 1 = picked, 0 = cancelled */
#define MENU_ALLOW_MASK         (*(volatile u16 *)0x021CEB64)  /* bit n: slot n can be picked */
#define FN_POCKET_ITEM_AT       ((u16 (*)(int slot))(0x02099394 | 1))

/* ov047: Blathers */
#define FN_OPEN_DONATE          ((void (*)(u32 talk))(0x0225D1C4 | 1))
#define FN_OPEN_ASSESS          ((void (*)(u32 talk))(0x0225D19C | 1))
#define FN_DONATE_PICKED        ((void (*)(u32 talk))(0x0225DD48 | 1))   /* ov047_blathers_item_reply */
#define FN_ASSESS_PICKED        ((void (*)(u32 talk))(0x0225DCA8 | 1))
#define FN_TALK_STEP            ((void (*)(u32 talk, u32 a1, u32 a2, u32 a3))(0x0225D1EC | 1))
#define TALK_MESSAGE            0x1E            /* u8: message being shown */
#define MSG_FIRST_TOPIC         0x0C            /* lower ones are the greeting */

static u16 s_marks;             /* pocket slots set aside in the picker */
static u16 s_items[15];         /* the item each one held */
static u8 s_armed;              /* Blathers' picker is open */

/* Hook: ov101 sub-state 6 (member-pointer table entry). Only acts while Blathers' picker is open. */
void hook_picker_grid(u8 *pk) {
    int slot = pk[PK_CURSOR];
    if (s_armed && slot < 15) {
        u16 bit = 1 << slot;
        void *ring = pk + PK_MARK_BITS;
        if (PAD_PRESSED & KEY_X) {
            if (s_marks & bit) {
                s_marks &= ~bit;
                FN_BITS_CLEAR(ring, slot);
            } else if (MENU_ALLOW_MASK & bit) {
                u16 item = FN_POCKET_ITEM_AT(slot);
                if (item != ITEM_EMPTY) {
                    s_marks |= bit;
                    s_items[slot] = item;
                    FN_BITS_SET(ring, slot);
                }
            }
        } else if ((PAD_PRESSED & KEY_A) && (s_marks & bit)) {
            s_marks &= ~bit;              /* picking a marked slot: vanilla handles it, so it is no mark any more */
            FN_BITS_CLEAR(ring, slot);
        }
    }
    FN_PICKER_GRID(pk);
}

/* Hands the next marked slot to Blathers as if picked. 1 = done, 0 = nothing left (marks cleared). */
static int feed_next(u32 talk, void (*picked)(u32)) {
    int slot;
    for (slot = 0; slot < 15 && s_marks; slot++) {
        u16 bit = 1 << slot;
        if (!(s_marks & bit)) {
            continue;
        }
        s_marks &= ~bit;
        if (FN_POCKET_ITEM_AT(slot) == s_items[slot]) {
            MENU_CHOSEN_INDEX = slot;
            MENU_CHOSEN_FLAG = 1;
            picked(talk);
            return 1;
        }
    }
    s_marks = 0;
    return 0;
}

/* Hooks: the talk-choice handlers that open the picker (member-pointer pairs in ov047's choice table). */
void hook_blathers_open_donate(u32 talk) {
    if (!feed_next(talk, FN_DONATE_PICKED)) {
        s_armed = 1;
        FN_OPEN_DONATE(talk);
    }
}

void hook_blathers_open_assess(u32 talk) {
    if (!feed_next(talk, FN_ASSESS_PICKED)) {
        s_armed = 1;
        FN_OPEN_ASSESS(talk);
    }
}

/* Hooks: what runs when the picker closes (ov047's after-menu table). */
void hook_blathers_donate_picked(u32 talk) {
    s_armed = 0;
    if (MENU_CHOSEN_FLAG != 1) {
        s_marks = 0;
    }
    FN_DONATE_PICKED(talk);
}

void hook_blathers_assess_picked(u32 talk) {
    s_armed = 0;
    if (MENU_CHOSEN_FLAG != 1) {
        s_marks = 0;
    }
    FN_ASSESS_PICKED(talk);
}

/* Hook: Blathers' talk step (vtable). A new conversation (greeting) drops what was left over from the last one. */
void hook_blathers_step(u32 talk, u32 a1, u32 a2, u32 a3) {
    if (*(u8 *)(talk + TALK_MESSAGE) < MSG_FIRST_TOPIC) {
        s_marks = 0;
        s_armed = 0;
    }
    FN_TALK_STEP(talk, a1, a2, a3);
}
