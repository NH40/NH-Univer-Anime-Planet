from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import (
    RELIC_BATTLE_GAME_DEADLINE_HOURS,
    RELIC_BATTLE_GAMES_PER_MATCH,
    RELIC_BATTLE_THROWS_PER_GAME,
    RELIC_GAME_EMOJI,
)
from bot.constant.celestial import (
    CB_CELESTIAL_ACCEPT_PREFIX,
    CB_CELESTIAL_CARD_PREFIX,
    CB_CELESTIAL_DECLINE_CONFIRM_PREFIX,
    CB_CELESTIAL_DECLINE_PREFIX,
    CB_CELESTIAL_OPEN,
    CB_CELESTIAL_THROW_PREFIX,
    LOCK_ACTION_CELESTIAL_ACCEPT,
    LOCK_ACTION_CELESTIAL_DECLINE,
    LOCK_ACTION_CELESTIAL_THROW,
)
from bot.db.models.card import Card
from bot.db.models.celestial_battle import CelestialBattle
from bot.db.repositories.card import get_by_id as get_card_by_id
from bot.db.repositories.celestial import CelestialCardStatus
from bot.db.repositories.celestial import get_battle as get_celestial_battle
from bot.db.repositories.celestial import get_ownership as get_celestial_ownership
from bot.db.repositories.celestial import list_all_statuses
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.universe import get_by_code as get_universe_by_code
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.keyboards.celestial import celestial_detail_menu, celestial_list_menu, decline_confirm_menu, push_throw_menu
from bot.services import celestial as celestial_service
from bot.texts.celestial import (
    CELESTIAL_ACCEPT_DONE,
    CELESTIAL_ALREADY_THREW_ALERT,
    CELESTIAL_DECLINE_CONFIRM,
    CELESTIAL_DECLINE_DONE,
    CELESTIAL_DETAIL_BATTLE_LINE,
    CELESTIAL_DETAIL_CHALLENGER_LINE,
    CELESTIAL_DETAIL_FREE,
    CELESTIAL_DETAIL_HEADER,
    CELESTIAL_DETAIL_OWNER_LINE,
    CELESTIAL_DETAIL_YOUR_THROWS,
    CELESTIAL_GAME_EXPIRED_ALERT,
    CELESTIAL_LIST_EMPTY,
    CELESTIAL_LIST_HEADER,
    CELESTIAL_NOT_CHALLENGED_ALERT,
    CELESTIAL_NOT_PARTICIPANT_ALERT,
    CELESTIAL_NO_BATTLE_ALERT,
    CELESTIAL_PUSH_BATTLE_STARTED,
    CELESTIAL_PUSH_GAINED_TIMEOUT,
    CELESTIAL_PUSH_LOST_DECLINE,
    CELESTIAL_PUSH_LOST_TIMEOUT,
    CELESTIAL_PUSH_MATCH_LOST_CHALLENGER,
    CELESTIAL_PUSH_MATCH_LOST_OWNER,
    CELESTIAL_PUSH_MATCH_WON_CHALLENGER,
    CELESTIAL_PUSH_MATCH_WON_OWNER,
    CELESTIAL_PUSH_NEXT_GAME,
    DIVINE_PUSH_GLOBAL,
    DIVINE_PUSH_PSEUDO,
    DIVINE_PUSH_UNIVERSE,
    GAME_NAMES,
)
from bot.utils.formatting import esc, format_countdown
from bot.utils.safe_edit import safe_edit_text

router = Router(name="celestial")


async def _notify(bot: Bot, user_id: int, text: str, *, reply_markup=None) -> None:
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup)
    except TelegramAPIError:
        pass


# Крошечный процессный кэш заголовков вселенных для текста пуша божественной карты —
# вселенных считанные единицы, перечитывать их из БД на каждый пуш незачем (ttl не нужен,
# заголовки вселенных меняются только вручную админом и крайне редко).
_universe_title_cache: dict[str, str] = {}


async def _universe_title(session: AsyncSession, universe_code: str) -> str:
    if universe_code not in _universe_title_cache:
        universe = await get_universe_by_code(session, universe_code)
        _universe_title_cache[universe_code] = universe.title if universe else universe_code
    return _universe_title_cache[universe_code]


async def notify_divine_grant(bot: Bot, session: AsyncSession, grant: celestial_service.DivineGrant) -> None:
    if grant.card.is_divine_pseudo:
        text = DIVINE_PUSH_PSEUDO.format(name=esc(grant.card.name))
    elif grant.card.is_divine_global:
        text = DIVINE_PUSH_GLOBAL.format(name=esc(grant.card.name))
    else:
        universe = await _universe_title(session, grant.card.universe_code)
        text = DIVINE_PUSH_UNIVERSE.format(universe=esc(universe), name=esc(grant.card.name))
    await _notify(bot, grant.user_id, text)


def _current_game(battle: CelestialBattle) -> str:
    return (battle.game_1, battle.game_2, battle.game_3)[battle.game_index]


async def _render_detail(session: AsyncSession, status: CelestialCardStatus, *, viewer_id: int) -> tuple[str, object]:
    universe_title = await _universe_title(session, status.card.universe_code)
    text = CELESTIAL_DETAIL_HEADER.format(name=esc(status.card.name), universe=esc(universe_title))
    ownership = status.ownership
    battle = status.battle
    current_game: str | None = None
    can_throw = False

    if ownership is None:
        text += CELESTIAL_DETAIL_FREE
    else:
        owner = await get_user_by_id(session, ownership.owner_id)
        text += CELESTIAL_DETAIL_OWNER_LINE.format(name=esc(owner.display_name or "—") if owner else "—")

        if battle is not None:
            current_game = _current_game(battle)
            challenger = await get_user_by_id(session, battle.challenger_id)
            text += CELESTIAL_DETAIL_CHALLENGER_LINE.format(
                name=esc(challenger.display_name or "—") if challenger else "—",
                deadline=format_countdown(max(0, int((battle.game_deadline_at - datetime.now(timezone.utc)).total_seconds()))),
            )
            text += CELESTIAL_DETAIL_BATTLE_LINE.format(
                game_num=battle.game_index + 1,
                total_games=RELIC_BATTLE_GAMES_PER_MATCH,
                game=GAME_NAMES.get(current_game, current_game),
                owner_wins=battle.owner_wins,
                challenger_wins=battle.challenger_wins,
            )
            if viewer_id in (battle.owner_id, battle.challenger_id):
                is_owner = viewer_id == battle.owner_id
                count = battle.owner_throw_count if is_owner else battle.challenger_throw_count
                throw_sum = battle.owner_throw_sum if is_owner else battle.challenger_throw_sum
                text += CELESTIAL_DETAIL_YOUR_THROWS.format(count=count, max=RELIC_BATTLE_THROWS_PER_GAME, sum=throw_sum)
                can_throw = count < RELIC_BATTLE_THROWS_PER_GAME and datetime.now(timezone.utc) < battle.game_deadline_at
        elif ownership.challenger_id is not None:
            challenger = await get_user_by_id(session, ownership.challenger_id)
            seconds = max(0, int((ownership.challenge_deadline_at - datetime.now(timezone.utc)).total_seconds()))
            text += CELESTIAL_DETAIL_CHALLENGER_LINE.format(
                name=esc(challenger.display_name or "—") if challenger else "—", deadline=format_countdown(seconds)
            )

    markup = celestial_detail_menu(status, viewer_id=viewer_id, current_game=current_game, can_throw=can_throw)
    return text, markup


async def show_list(target: Message, session: AsyncSession, *, edit: bool) -> None:
    statuses = await list_all_statuses(session)
    if not statuses:
        text, markup = CELESTIAL_LIST_HEADER + CELESTIAL_LIST_EMPTY, None
    else:
        text, markup = CELESTIAL_LIST_HEADER, celestial_list_menu(statuses)
    if edit:
        await safe_edit_text(target, text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.callback_query(F.data == CB_CELESTIAL_OPEN)
async def cb_open_celestial(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await show_list(callback.message, session, edit=True)


@router.callback_query(F.data.startswith(CB_CELESTIAL_CARD_PREFIX))
async def cb_open_card(callback: CallbackQuery, session: AsyncSession) -> None:
    card_id = int(callback.data[len(CB_CELESTIAL_CARD_PREFIX) :])
    statuses = await list_all_statuses(session)
    status = next((s for s in statuses if s.card.id == card_id), None)
    await callback.answer()
    if status is None:
        await show_list(callback.message, session, edit=True)
        return
    text, markup = await _render_detail(session, status, viewer_id=callback.from_user.id)
    await safe_edit_text(callback.message, text, reply_markup=markup)


@router.callback_query(F.data.startswith(CB_CELESTIAL_ACCEPT_PREFIX))
async def cb_accept(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    card_id = int(callback.data[len(CB_CELESTIAL_ACCEPT_PREFIX) :])
    owner_id = callback.from_user.id

    async with try_acquire(redis, action_lock(owner_id, LOCK_ACTION_CELESTIAL_ACCEPT)) as acquired:
        if not acquired:
            await callback.answer()
            return
        try:
            battle = await celestial_service.accept_challenge(session, card_id=card_id, owner_id=owner_id)
        except celestial_service.NotChallengedError:
            await callback.answer(CELESTIAL_NOT_CHALLENGED_ALERT, show_alert=True)
            return

        card = await get_card_by_id(session, card_id)
        game = _current_game(battle)
        emoji = RELIC_GAME_EMOJI.get(game, "🎲")
        game_name = GAME_NAMES.get(game, game)

        await callback.answer(CELESTIAL_ACCEPT_DONE.format(emoji=emoji, game=game_name))
        text = CELESTIAL_PUSH_BATTLE_STARTED.format(
            name=esc(card.name), total=RELIC_BATTLE_GAMES_PER_MATCH, emoji=emoji, game=game_name, hours=RELIC_BATTLE_GAME_DEADLINE_HOURS
        )
        markup = push_throw_menu(card_id, game=game)
        await _notify(bot, owner_id, text, reply_markup=markup)
        await _notify(bot, battle.challenger_id, text, reply_markup=markup)


@router.callback_query(F.data.startswith(CB_CELESTIAL_DECLINE_CONFIRM_PREFIX))
async def cb_decline_confirm(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    card_id = int(callback.data[len(CB_CELESTIAL_DECLINE_CONFIRM_PREFIX) :])
    owner_id = callback.from_user.id

    async with try_acquire(redis, action_lock(owner_id, LOCK_ACTION_CELESTIAL_DECLINE)) as acquired:
        if not acquired:
            await callback.answer()
            return

        season = await get_active_season(session)
        if season is None:
            await callback.answer()
            return
        card = await get_card_by_id(session, card_id)
        try:
            challenger_id, awards = await celestial_service.decline_challenge(
                session, card_id=card_id, owner_id=owner_id, season_id=season.id
            )
        except celestial_service.NotChallengedError:
            await callback.answer(CELESTIAL_NOT_CHALLENGED_ALERT, show_alert=True)
            return

        await callback.answer(CELESTIAL_DECLINE_DONE)
        await _notify(bot, challenger_id, CELESTIAL_PUSH_LOST_DECLINE.format(name=esc(card.name)))
        for grant in awards.grants:
            await celestial_service.sync_grant(redis, season.id, grant)
            await notify_divine_grant(bot, session, grant)


@router.callback_query(F.data.startswith(CB_CELESTIAL_DECLINE_PREFIX))
async def cb_decline_ask(callback: CallbackQuery) -> None:
    card_id = int(callback.data[len(CB_CELESTIAL_DECLINE_PREFIX) :])
    await callback.answer()
    await callback.message.answer(CELESTIAL_DECLINE_CONFIRM, reply_markup=decline_confirm_menu(card_id))


@router.callback_query(F.data.startswith(CB_CELESTIAL_THROW_PREFIX))
async def cb_throw(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    card_id = int(callback.data[len(CB_CELESTIAL_THROW_PREFIX) :])
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CELESTIAL_THROW)) as acquired:
        if not acquired:
            await callback.answer()
            return

        ownership = await get_celestial_ownership(session, card_id)
        if ownership is None:
            await callback.answer(CELESTIAL_NO_BATTLE_ALERT, show_alert=True)
            return

        season = await get_active_season(session)
        if season is None:
            await callback.answer()
            return

        # Само значение броска получаем через Bot API ДО вызова сервиса (см. CLAUDE.md,
        # правило 10 — I/O с Telegram не место в сервисном слое). Игра текущего боя нужна
        # заранее, чтобы бросить кубик нужным эмодзи — throw_dice сам перепроверит
        # дедлайн/участие атомарно и кинет исключение при необходимости, этот запрос
        # только для выбора эмодзи, без мутаций.
        card = await get_card_by_id(session, card_id)
        battle = await get_celestial_battle(session, card_id)
        if battle is None:
            await callback.answer(CELESTIAL_NO_BATTLE_ALERT, show_alert=True)
            return
        if user_id not in (battle.owner_id, battle.challenger_id):
            await callback.answer(CELESTIAL_NOT_PARTICIPANT_ALERT, show_alert=True)
            return
        game = _current_game(battle)

        await callback.answer()
        dice_message = await callback.message.answer_dice(emoji=RELIC_GAME_EMOJI.get(game, "🎲"))
        value = dice_message.dice.value

        try:
            result = await celestial_service.throw_dice(
                session, card_id=card_id, user_id=user_id, roll_value=value, season_id=season.id
            )
        except celestial_service.NoBattleError:
            await callback.message.answer(CELESTIAL_NO_BATTLE_ALERT)
            return
        except celestial_service.NotParticipantError:
            await callback.message.answer(CELESTIAL_NOT_PARTICIPANT_ALERT)
            return
        except celestial_service.AlreadyThrewError:
            await callback.message.answer(CELESTIAL_ALREADY_THREW_ALERT)
            return
        except celestial_service.GameExpiredError:
            await callback.message.answer(CELESTIAL_GAME_EXPIRED_ALERT)
            return

        await _handle_throw_result(bot, redis, session, season_id=season.id, card=card, result=result)


async def _handle_throw_result(
    bot: Bot, redis: Redis, session: AsyncSession, *, season_id: int, card: Card, result: celestial_service.ThrowResult
) -> None:
    owner_id, challenger_id = result.owner_id, result.challenger_id
    if not result.game_finished:
        return  # ждём, пока и соперник добросит свои RELIC_BATTLE_THROWS_PER_GAME

    battle = result.battle  # None, если матч только что завершился целиком
    if not result.match_finished and battle is not None:
        # Броски уже сброшены на новую игру advance_game'ом — итоги ПРОШЕДШЕЙ игры видны
        # только через wins-счётчик (в тексте следующего анонса), отдельно суммы прошлой
        # игры здесь не нужны.
        next_game = _current_game(battle)
        emoji = RELIC_GAME_EMOJI.get(next_game, "🎲")
        game_name = GAME_NAMES.get(next_game, next_game)
        text = CELESTIAL_PUSH_NEXT_GAME.format(
            owner_wins=battle.owner_wins,
            challenger_wins=battle.challenger_wins,
            game_num=battle.game_index + 1,
            total=RELIC_BATTLE_GAMES_PER_MATCH,
            emoji=emoji,
            game=game_name,
            hours=RELIC_BATTLE_GAME_DEADLINE_HOURS,
        )
        markup = push_throw_menu(card.id, game=next_game)
        await _notify(bot, owner_id, text, reply_markup=markup)
        await _notify(bot, challenger_id, text, reply_markup=markup)
        return

    if not result.match_finished:
        return  # техническое поражение в игре, но не в матче, и это sweep без battle (не должно происходить) — не о чем уведомлять

    # Матч завершён.
    new_owner_id = result.new_owner_id
    if new_owner_id == owner_id:
        await _notify(bot, owner_id, CELESTIAL_PUSH_MATCH_WON_OWNER.format(name=esc(card.name)))
        await _notify(bot, challenger_id, CELESTIAL_PUSH_MATCH_LOST_CHALLENGER.format(name=esc(card.name)))
    else:
        await _notify(bot, challenger_id, CELESTIAL_PUSH_MATCH_WON_CHALLENGER.format(name=esc(card.name)))
        await _notify(bot, owner_id, CELESTIAL_PUSH_MATCH_LOST_OWNER.format(name=esc(card.name)))

    if result.divine_awards:
        for grant in result.divine_awards.grants:
            await celestial_service.sync_grant(redis, season_id, grant)
            await notify_divine_grant(bot, session, grant)


# --- Фоновый sweep (см. main.py: переиспользует существующий 5-минутный цикл services/notify) ---


async def run_sweep(bot: Bot, session: AsyncSession, redis: Redis) -> None:
    season = await get_active_season(session)
    if season is None:
        return

    for card_id, old_owner_id, new_owner_id, awards in await celestial_service.sweep_expired_decisions(session, season_id=season.id):
        card = await get_card_by_id(session, card_id)
        await _notify(bot, old_owner_id, CELESTIAL_PUSH_LOST_TIMEOUT.format(name=esc(card.name)))
        await _notify(bot, new_owner_id, CELESTIAL_PUSH_GAINED_TIMEOUT.format(name=esc(card.name)))
        for grant in awards.grants:
            await celestial_service.sync_grant(redis, season.id, grant)
            await notify_divine_grant(bot, session, grant)

    for result in await celestial_service.sweep_expired_games(session, season_id=season.id):
        card = await get_card_by_id(session, result.card_id)
        await _handle_throw_result(bot, redis, session, season_id=season.id, card=card, result=result)
