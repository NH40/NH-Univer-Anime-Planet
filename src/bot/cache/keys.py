"""Единая схема ключей Redis — чтобы не разбредались по хендлерам/сервисам."""

from __future__ import annotations


def action_lock(user_id: int, action: str) -> str:
    """Антидубликат-лок на время обработки одного действия (SET NX PX)."""
    return f"lock:{user_id}:{action}"


def leaderboard_players_season(season_id: int) -> str:
    return f"leaderboard:players:season:{season_id}"


def tech_mode_flag() -> str:
    return "flag:tech_mode"


def card_file_id(card_id: int) -> str:
    """Кэш Telegram file_id по карточке (см. utils/card_media) — картинка одна и та же
    независимо от звезды, поэтому ключ только по card_id, не по (card_id, stars)."""
    return f"cache:card_file_id:{card_id}"


def wipe_confirm_flag(user_id: int) -> str:
    """Анти-replay для двух последовательных нажатий подтверждения полного сброса БД
    (см. services/admin/wipe) — короткий TTL, чтобы подтверждение, забытое на часы, не
    сработало случайно спустя время."""
    return f"flag:wipe_confirm:{user_id}"


def throttle_flag(user_id: int) -> str:
    """Общий антифлуд (см. middlewares/throttling.py) — не путать с action_lock: тот
    защищает конкретное resource-affecting действие от повторного клика (правило 2),
    этот — общий предохранитель от спама ЛЮБЫМИ апдейтами одного игрока подряд."""
    return f"throttle:{user_id}"
