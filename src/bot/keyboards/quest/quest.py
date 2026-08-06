from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.quest import CB_QUEST_CLAIM_ALL, CB_QUEST_CLAIM_PREFIX, CB_QUEST_REROLL_ALL, CB_QUEST_REROLL_PREFIX
from bot.services.quest import QuestScreenStatus
from bot.texts.quest import BTN_QUEST_CLAIM_ALL, BTN_QUEST_CLAIM_PREFIX, BTN_QUEST_REROLL_ALL, BTN_QUEST_REROLL_PREFIX


def quests_menu(status: QuestScreenStatus) -> InlineKeyboardMarkup:
    """Кнопка на слот — либо "Забрать" (выполнено, не забрано), либо "Переролить" (не
    выполнено, не забрано, есть индивидуальные рероллы). Уже забранные слоты — без кнопки.
    Снизу — общие "Забрать всё"/"Переролить всё", только если применимо хоть к чему-то."""
    rows: list[list[InlineKeyboardButton]] = []
    any_claimable = False
    for slot_view in status.slots:
        if slot_view.claimed:
            continue
        if slot_view.done:
            any_claimable = True
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{BTN_QUEST_CLAIM_PREFIX}{slot_view.slot + 1}",
                        callback_data=f"{CB_QUEST_CLAIM_PREFIX}{slot_view.slot}",
                    )
                ]
            )
        elif status.individual_rerolls_left > 0:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{BTN_QUEST_REROLL_PREFIX}{slot_view.slot + 1}",
                        callback_data=f"{CB_QUEST_REROLL_PREFIX}{slot_view.slot}",
                    )
                ]
            )

    bottom_row: list[InlineKeyboardButton] = []
    if any_claimable:
        bottom_row.append(InlineKeyboardButton(text=BTN_QUEST_CLAIM_ALL, callback_data=CB_QUEST_CLAIM_ALL))
    if status.reroll_all_available:
        bottom_row.append(InlineKeyboardButton(text=BTN_QUEST_REROLL_ALL, callback_data=CB_QUEST_REROLL_ALL))
    if bottom_row:
        rows.append(bottom_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)
