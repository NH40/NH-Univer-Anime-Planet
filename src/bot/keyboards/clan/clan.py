from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.clan import (
    CB_CLAN_ACCEPT_INVITE_PREFIX,
    CB_CLAN_ACCEPT_PREFIX,
    CB_CLAN_APPLY_PREFIX,
    CB_CLAN_CANCEL_APPLICATION_PREFIX,
    CB_CLAN_CREATE_START,
    CB_CLAN_DECLINE_INVITE_PREFIX,
    CB_CLAN_EDIT,
    CB_CLAN_EDIT_DESCRIPTION,
    CB_CLAN_EDIT_IMAGE,
    CB_CLAN_EDIT_NAME,
    CB_CLAN_EXCHANGE_CURRENCY_PREFIX,
    CB_CLAN_EXCHANGE_START,
    CB_CLAN_FIND,
    CB_CLAN_FIND_PAGE_PREFIX,
    CB_CLAN_INVITE_START,
    CB_CLAN_LEAVE,
    CB_CLAN_LEAVE_CONFIRM,
    CB_CLAN_MEMBERS,
    CB_CLAN_MY_INVITES,
    CB_CLAN_OPEN,
    CB_CLAN_RANKS,
    CB_CLAN_REJECT_PREFIX,
    CB_CLAN_REQUESTS,
    CB_CLAN_SET_RANK_PREFIX,
    CB_CLAN_TRANSFER_CONFIRM_PREFIX,
    CB_CLAN_TRANSFER_START,
    CB_CLAN_VIEW_PREFIX,
    CB_CLAN_WAR,
    CB_CLAN_WAR_START,
    CB_CLAN_WAR_TARGET_PREFIX,
    CB_TOPCLAN_PAGE_PREFIX,
    CB_TOPCLAN_TOGGLE_PREFIX,
)
from bot.db.models.clan import Clan
from bot.db.models.enums import ClanRank
from bot.texts.clan import (
    BTN_ACCEPT,
    BTN_ACCEPT_INVITE,
    BTN_APPLY,
    BTN_CANCEL_APPLICATION,
    BTN_CREATE_CLAN,
    BTN_DECLINE_INVITE,
    BTN_EDIT,
    BTN_EDIT_DESCRIPTION,
    BTN_EDIT_IMAGE,
    BTN_EDIT_NAME,
    BTN_EXCHANGE,
    BTN_EXCHANGE_COINS,
    BTN_EXCHANGE_DUST,
    BTN_EXCHANGE_TICKETS,
    BTN_FIND_CLAN,
    BTN_INVITE,
    BTN_LEAVE,
    BTN_MEMBERS,
    BTN_MY_INVITES,
    BTN_RANKS,
    BTN_REJECT,
    BTN_REQUESTS,
    BTN_START_WAR,
    BTN_TOPCLAN_TOGGLE_SEASON,
    BTN_TOPCLAN_TOGGLE_TOTAL,
    BTN_TRANSFER,
    BTN_WAR,
)
from bot.services.clan import MANAGER_RANKS
from bot.texts.common import BTN_BACK

RANK_LABELS = {
    ClanRank.member: "Участник",
    ClanRank.captain: "Капитан",
    ClanRank.deputy: "Заместитель",
}


def no_clan_menu(*, invite_count: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BTN_CREATE_CLAN, callback_data=CB_CLAN_CREATE_START)],
        [InlineKeyboardButton(text=BTN_FIND_CLAN, callback_data=CB_CLAN_FIND)],
    ]
    if invite_count:
        rows.append(
            [InlineKeyboardButton(text=BTN_MY_INVITES.format(count=invite_count), callback_data=CB_CLAN_MY_INVITES)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def exchange_currency_menu() -> InlineKeyboardMarkup:
    """Шаг выбора валюты перед вводом @username/суммы (см. CLAUDE.md, "Кланы" — обменник
    обобщён с пыли на пыль/тикеты/коины). Суффикс callback'а — значение TransactionCurrency
    (см. handlers/clan/exchange.py: cb_exchange_currency)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_EXCHANGE_DUST, callback_data=f"{CB_CLAN_EXCHANGE_CURRENCY_PREFIX}dust")],
            [InlineKeyboardButton(text=BTN_EXCHANGE_TICKETS, callback_data=f"{CB_CLAN_EXCHANGE_CURRENCY_PREFIX}tickets")],
            [InlineKeyboardButton(text=BTN_EXCHANGE_COINS, callback_data=f"{CB_CLAN_EXCHANGE_CURRENCY_PREFIX}coins")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)],
        ]
    )


def clan_card_menu(*, rank: ClanRank, request_count: int = 0) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BTN_MEMBERS, callback_data=CB_CLAN_MEMBERS)],
        [InlineKeyboardButton(text=BTN_EXCHANGE, callback_data=CB_CLAN_EXCHANGE_START)],
        [InlineKeyboardButton(text=BTN_WAR, callback_data=CB_CLAN_WAR)],
    ]
    if rank in MANAGER_RANKS:
        rows.append(
            [
                InlineKeyboardButton(text=BTN_REQUESTS.format(count=request_count), callback_data=CB_CLAN_REQUESTS),
                InlineKeyboardButton(text=BTN_INVITE, callback_data=CB_CLAN_INVITE_START),
            ]
        )
        rows.append([InlineKeyboardButton(text=BTN_EDIT, callback_data=CB_CLAN_EDIT)])
    if rank == ClanRank.owner:
        rows.append([InlineKeyboardButton(text=BTN_RANKS, callback_data=CB_CLAN_RANKS)])
    rows.append([InlineKeyboardButton(text=BTN_LEAVE, callback_data=CB_CLAN_LEAVE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def find_clans_menu(rows_data: list[tuple[Clan, int, int]], *, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=clan.name, callback_data=f"{CB_CLAN_VIEW_PREFIX}{clan.id}")]
        for clan, _ubp, _cnt in rows_data
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Назад", callback_data=f"{CB_CLAN_FIND_PAGE_PREFIX}{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"{CB_CLAN_FIND_PAGE_PREFIX}{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_view_menu(*, clan_id: int, has_applied: bool, can_apply: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_apply:
        if has_applied:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=BTN_CANCEL_APPLICATION, callback_data=f"{CB_CLAN_CANCEL_APPLICATION_PREFIX}{clan_id}"
                    )
                ]
            )
        else:
            rows.append([InlineKeyboardButton(text=BTN_APPLY, callback_data=f"{CB_CLAN_APPLY_PREFIX}{clan_id}")])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_FIND)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_clan_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)]])


def requests_menu(requests: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """requests — список (user_id, username)."""
    rows = [
        [
            InlineKeyboardButton(text=BTN_ACCEPT.format(username=username), callback_data=f"{CB_CLAN_ACCEPT_PREFIX}{uid}"),
            InlineKeyboardButton(text=BTN_REJECT.format(username=username), callback_data=f"{CB_CLAN_REJECT_PREFIX}{uid}"),
        ]
        for uid, username in requests
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_invites_menu(invites: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """invites — список (clan_id, clan_name)."""
    rows: list[list[InlineKeyboardButton]] = []
    for cid, name in invites:
        rows.append(
            [InlineKeyboardButton(text=BTN_ACCEPT_INVITE.format(clan_name=name), callback_data=f"{CB_CLAN_ACCEPT_INVITE_PREFIX}{cid}")]
        )
        rows.append(
            [InlineKeyboardButton(text=BTN_DECLINE_INVITE.format(clan_name=name), callback_data=f"{CB_CLAN_DECLINE_INVITE_PREFIX}{cid}")]
        )
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ranks_menu(members: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """members — (user_id, display_name), без владельца."""
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{CB_CLAN_SET_RANK_PREFIX}{uid}")] for uid, name in members
    ]
    rows.append([InlineKeyboardButton(text=BTN_TRANSFER, callback_data=CB_CLAN_TRANSFER_START)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rank_set_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{CB_CLAN_SET_RANK_PREFIX}{user_id}:{rank.value}")]
        for rank, label in RANK_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_RANKS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def transfer_menu(members: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{CB_CLAN_TRANSFER_CONFIRM_PREFIX}{uid}")]
        for uid, name in members
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def transfer_confirm_menu(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{CB_CLAN_TRANSFER_CONFIRM_PREFIX}{user_id}:confirm")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_TRANSFER_START)],
        ]
    )


def edit_menu(*, can_set_image: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BTN_EDIT_NAME, callback_data=CB_CLAN_EDIT_NAME)],
        [InlineKeyboardButton(text=BTN_EDIT_DESCRIPTION, callback_data=CB_CLAN_EDIT_DESCRIPTION)],
    ]
    if can_set_image:
        rows.append([InlineKeyboardButton(text=BTN_EDIT_IMAGE, callback_data=CB_CLAN_EDIT_IMAGE)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def war_menu(*, can_manage: bool, has_active_war: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_manage and not has_active_war:
        rows.append([InlineKeyboardButton(text=BTN_START_WAR, callback_data=CB_CLAN_WAR_START)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def war_target_menu(rows_data: list[tuple[Clan, int, int]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=clan.name, callback_data=f"{CB_CLAN_WAR_TARGET_PREFIX}{clan.id}")]
        for clan, _ubp, _cnt in rows_data
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_WAR)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def leave_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=CB_CLAN_LEAVE_CONFIRM)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CLAN_OPEN)],
        ]
    )


def topclan_menu(*, page: int, total_pages: int, by_total: bool) -> InlineKeyboardMarkup:
    """Кнопки пагинации/переключения режима несут текущую страницу и режим (0/1) в
    callback_data — иначе следующий клик не знал бы, сезон сейчас показан или всё время."""
    mode_flag = int(by_total)
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="« Назад", callback_data=f"{CB_TOPCLAN_PAGE_PREFIX}{page - 1}:{mode_flag}")
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="Вперёд »", callback_data=f"{CB_TOPCLAN_PAGE_PREFIX}{page + 1}:{mode_flag}")
        )
    toggle_text = BTN_TOPCLAN_TOGGLE_SEASON if by_total else BTN_TOPCLAN_TOGGLE_TOTAL
    rows = [row for row in [nav] if row]
    rows.append([InlineKeyboardButton(text=toggle_text, callback_data=f"{CB_TOPCLAN_TOGGLE_PREFIX}{mode_flag}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
