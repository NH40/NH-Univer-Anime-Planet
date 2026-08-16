from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.settings import get_settings
from bot.constant.battle_pass import (
    CB_BATTLE_PASS_CLAIM_ALL_FREE,
    CB_BATTLE_PASS_CLAIM_ALL_PREMIUM,
    CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX,
    CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX,
    CB_BATTLE_PASS_LEVELS_PAGE_PREFIX,
    LOCK_ACTION_CLAIM_PASS_FREE,
    LOCK_ACTION_CLAIM_PASS_PREMIUM,
    TRACK_FREE,
    TRACK_PREMIUM,
)
from bot.keyboards.battle_pass import levels_menu
from bot.services import battle_pass as pass_service
from bot.texts.battle_pass import (
    PASS_BOOST_LINE,
    PASS_CLAIM_ALL_DONE,
    PASS_CLAIMED_DONE,
    PASS_HEADER,
    PASS_LEVEL_ALREADY_CLAIMED_ALERT,
    PASS_LEVEL_LOCKED_ALERT,
    PASS_NO_SEASON,
    PASS_NOT_PREMIUM_ALERT,
    PASS_NOTHING_TO_CLAIM_ALERT,
    PASS_PREMIUM_ACTIVE,
    PASS_PREMIUM_LOCKED,
    PASS_REWARD_COINS_SUFFIX,
    PASS_REWARD_DUST_ONLY,
    PASS_REWARD_DUST_TICKETS,
    PASS_REWARD_TICKETS_ONLY,
)
from bot.utils.formatting import format_countdown, progress_bar
from bot.utils.mini_app import resolve_mini_app_base_url
from bot.utils.safe_edit import safe_edit_text

router = Router(name="battle_pass_levels")

# 2 горизонтальные строки кнопок (премиум сверху, бесплатная снизу) вместо 10 вертикальных
# пар — подтверждено пользователем 2026-08-11 (см. CLAUDE.md, "клейм произвольной ячейки").
# Меньше, чем LEVELS_PER_PAGE у Mini App (та — горизонтально скроллящаяся лента, ей 10
# норм), потому что у бота ширина строки инлайн-кнопок Telegram ограничена практически.
_PAGE_SIZE = 5


def _reward_text(dust: int, tickets: int, coins: int = 0) -> str:
    if dust and tickets:
        text = PASS_REWARD_DUST_TICKETS.format(dust=dust, tickets=tickets)
    elif tickets:
        text = PASS_REWARD_TICKETS_ONLY.format(tickets=tickets)
    else:
        text = PASS_REWARD_DUST_ONLY.format(dust=dust)
    if coins:
        text += PASS_REWARD_COINS_SUFFIX.format(coins=coins)
    return text


def _render(page_view: pass_service.LevelsPage, *, mini_app_url: str | None) -> tuple[str, InlineKeyboardMarkup]:
    have = page_view.progress - page_view.level_floor
    need = page_view.level_ceiling - page_view.level_floor
    percent = round(100 * have / need) if need else 100
    boost_line = PASS_BOOST_LINE.format(
        multiplier=page_view.boost.multiplier,
        used=page_view.boost.used_today,
        cap=page_view.boost.cap,
        countdown=format_countdown(page_view.boost.seconds_until_reset),
    )
    text = PASS_HEADER.format(
        level=page_view.current_level,
        bar=progress_bar(percent),
        percent=percent,
        have=have,
        need=need,
        premium_status=PASS_PREMIUM_ACTIVE if page_view.is_premium else PASS_PREMIUM_LOCKED,
        boost_line=boost_line,
        page=page_view.page,
        total_pages=page_view.total_pages,
    )
    return text, levels_menu(page_view, mini_app_url=mini_app_url)


async def show_page(target: Message, session: AsyncSession, user_id: int, *, page: int | None, edit: bool) -> None:
    settings = get_settings()
    page_view = await pass_service.list_levels(session, user_id=user_id, page=page, per_page=_PAGE_SIZE)
    if page_view is None:
        if edit:
            await safe_edit_text(target, PASS_NO_SEASON)
        else:
            await target.answer(PASS_NO_SEASON)
        return
    mini_app_url = resolve_mini_app_base_url(settings.mini_app_url, target.chat.type)
    text, keyboard = _render(page_view, mini_app_url=mini_app_url)
    if edit:
        await safe_edit_text(target, text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)


def _parse_page_level(data: str, prefix: str) -> tuple[int, int]:
    page_str, _, level_str = data[len(prefix) :].partition(":")
    return int(page_str), int(level_str)


def _parse_page(data: str, prefix: str) -> int:
    try:
        return int(data[len(prefix) :])
    except ValueError:
        return 1


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_PAGE_PREFIX))
async def cb_open_page(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    page = _parse_page(callback.data, CB_BATTLE_PASS_LEVELS_PAGE_PREFIX)
    await show_page(callback.message, session, callback.from_user.id, page=page, edit=True)


async def _claim_level(
    callback: CallbackQuery,
    session: AsyncSession,
    redis: Redis,
    *,
    track: pass_service.Track,
    prefix: str,
    lock_action: str,
) -> None:
    user_id = callback.from_user.id
    page, level = _parse_page_level(callback.data, prefix)

    async with try_acquire(redis, action_lock(user_id, lock_action)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            dust, tickets, coins = await pass_service.claim_level(session, user_id=user_id, track=track, level=level)
        except pass_service.NoSeasonActiveError:
            await callback.answer(PASS_NO_SEASON, show_alert=True)
            return
        except pass_service.NotPremiumError:
            await callback.answer(PASS_NOT_PREMIUM_ALERT, show_alert=True)
            return
        except pass_service.LevelLockedError:
            await callback.answer(PASS_LEVEL_LOCKED_ALERT, show_alert=True)
            return
        except pass_service.LevelAlreadyClaimedError:
            await callback.answer(PASS_LEVEL_ALREADY_CLAIMED_ALERT, show_alert=True)
            return

        await callback.answer(PASS_CLAIMED_DONE.format(level=level, reward=_reward_text(dust, tickets, coins)))

    # Остаёмся на той же странице — тап по ячейке не должен никуда перебрасывать, игрок мог
    # кликать по остальным ячейкам этой же страницы дальше (см. CLAUDE.md).
    await show_page(callback.message, session, user_id, page=page, edit=True)


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX))
async def cb_claim_level_free(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _claim_level(
        callback,
        session,
        redis,
        track=TRACK_FREE,
        prefix=CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX,
        lock_action=LOCK_ACTION_CLAIM_PASS_FREE,
    )


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX))
async def cb_claim_level_premium(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _claim_level(
        callback,
        session,
        redis,
        track=TRACK_PREMIUM,
        prefix=CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX,
        lock_action=LOCK_ACTION_CLAIM_PASS_PREMIUM,
    )


async def _claim_all(
    callback: CallbackQuery, session: AsyncSession, redis: Redis, *, track: pass_service.Track, lock_action: str
) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, lock_action)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            result = await pass_service.claim_all(session, user_id=user_id, track=track)
        except pass_service.NoSeasonActiveError:
            await callback.answer(PASS_NO_SEASON, show_alert=True)
            return
        except pass_service.NotPremiumError:
            await callback.answer(PASS_NOT_PREMIUM_ALERT, show_alert=True)
            return
        except pass_service.NothingToClaimError:
            await callback.answer(PASS_NOTHING_TO_CLAIM_ALERT, show_alert=True)
            return

        await callback.answer(
            PASS_CLAIM_ALL_DONE.format(
                count=result.count, reward=_reward_text(result.dust, result.tickets, result.coins)
            ),
            show_alert=True,
        )

    # После "Забрать всё" — редирект на страницу с ТЕКУЩИМ уровнем (весь диапазон до него
    # только что забран целиком), а не оставаться на исходной странице (подтверждено
    # пользователем 2026-08-11, см. CLAUDE.md).
    target_page = pass_service.page_for_level(result.current_level, current_level=result.current_level, per_page=_PAGE_SIZE)
    await show_page(callback.message, session, user_id, page=target_page, edit=True)


@router.callback_query(F.data == CB_BATTLE_PASS_CLAIM_ALL_FREE)
async def cb_claim_all_free(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _claim_all(callback, session, redis, track=TRACK_FREE, lock_action=LOCK_ACTION_CLAIM_PASS_FREE)


@router.callback_query(F.data == CB_BATTLE_PASS_CLAIM_ALL_PREMIUM)
async def cb_claim_all_premium(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _claim_all(callback, session, redis, track=TRACK_PREMIUM, lock_action=LOCK_ACTION_CLAIM_PASS_PREMIUM)
