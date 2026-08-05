"""Единая схема ключей Redis — чтобы не разбредались по хендлерам/сервисам."""

from __future__ import annotations


def action_lock(user_id: int, action: str) -> str:
    """Антидубликат-лок на время обработки одного действия (SET NX PX)."""
    return f"lock:{user_id}:{action}"


def leaderboard_players_season(season_id: int) -> str:
    return f"leaderboard:players:season:{season_id}"


def tech_mode_flag() -> str:
    return "flag:tech_mode"


def throttle_flag(user_id: int) -> str:
    """Общий антифлуд (см. middlewares/throttling.py) — не путать с action_lock: тот
    защищает конкретное resource-affecting действие от повторного клика (правило 2),
    этот — общий предохранитель от спама ЛЮБЫМИ апдейтами одного игрока подряд."""
    return f"throttle:{user_id}"
