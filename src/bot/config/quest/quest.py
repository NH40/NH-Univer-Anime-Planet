from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bot.constant.casino import TRANSACTION_REASON_CASINO_MASS_ROLL, TRANSACTION_REASON_CASINO_ROLL
from bot.constant.clan import TRANSACTION_REASON_CLAN_EXCHANGE
from bot.constant.daily_bonus import TRANSACTION_REASON_DAILY_BONUS
from bot.constant.dust import TRANSACTION_REASON_DUST
from bot.constant.gacha import TRANSACTION_REASON_ROLL
from bot.constant.merge import TRANSACTION_REASON_MERGE
from bot.constant.shop import TRANSACTION_REASON_SHOP_COIN_TICKET, TRANSACTION_REASON_SHOP_TICKET
from bot.db.models.enums import TransactionCurrency

# Сколько заданий одновременно активно у игрока и лимиты рероллов — не игровой баланс наград
# (тот ниже, в QUEST_DEFS), а структурные параметры набора (см. CLAUDE.md, правило 8).
DAILY_QUEST_ACTIVE_SLOTS = 5
DAILY_QUEST_REFRESH_INTERVAL_HOURS = 24
DAILY_QUEST_REROLL_ALL_LIMIT = 1
DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT = 2

MetricMode = Literal["count", "sum_positive", "sum_abs_negative"]


@dataclass(frozen=True)
class QuestMetric:
    """Как считать прогресс: сколько строк `transactions` (count) или сумма их amount
    (sum_positive/sum_abs_negative), отфильтрованных по reason (+ опционально currency)
    и `created_at >= assigned_at` конкретного слота (см. services/quest/metrics.py) — та
    же "живая агрегация по журналу", что и остальная статистика в проекте (правило 3),
    без отдельного счётчика прогресса на задание."""

    reasons: tuple[str, ...]
    currency: TransactionCurrency | None
    mode: MetricMode


# Метрики переиспользуют УЖЕ существующие reason'ы из других доменов (см. CLAUDE.md,
# правило про constant/) — никакой новой инфраструктуры трекинга под задания не заводим.
QUEST_METRICS: dict[str, QuestMetric] = {
    "roll_actions": QuestMetric(reasons=(TRANSACTION_REASON_ROLL,), currency=None, mode="count"),
    "roll_ubp": QuestMetric(
        reasons=(TRANSACTION_REASON_ROLL,), currency=TransactionCurrency.ubp_season, mode="sum_positive"
    ),
    "merge_actions": QuestMetric(reasons=(TRANSACTION_REASON_MERGE,), currency=None, mode="count"),
    "merge_ubp": QuestMetric(
        reasons=(TRANSACTION_REASON_MERGE,), currency=TransactionCurrency.ubp_season, mode="sum_positive"
    ),
    "dust_earned": QuestMetric(
        reasons=(TRANSACTION_REASON_DUST,), currency=TransactionCurrency.dust, mode="sum_positive"
    ),
    "casino_plays": QuestMetric(
        reasons=(TRANSACTION_REASON_CASINO_ROLL, TRANSACTION_REASON_CASINO_MASS_ROLL),
        currency=TransactionCurrency.coins,
        mode="count",
    ),
    "casino_coins_spent": QuestMetric(
        reasons=(TRANSACTION_REASON_CASINO_ROLL, TRANSACTION_REASON_CASINO_MASS_ROLL),
        currency=TransactionCurrency.coins,
        mode="sum_abs_negative",
    ),
    "shop_ticket_purchases": QuestMetric(
        reasons=(TRANSACTION_REASON_SHOP_TICKET, TRANSACTION_REASON_SHOP_COIN_TICKET), currency=None, mode="count"
    ),
    "shop_dust_spent": QuestMetric(
        reasons=(TRANSACTION_REASON_SHOP_TICKET,), currency=TransactionCurrency.dust, mode="sum_abs_negative"
    ),
    "clan_exchange_participation": QuestMetric(
        reasons=(TRANSACTION_REASON_CLAN_EXCHANGE,), currency=None, mode="count"
    ),
    "daily_bonus_claims": QuestMetric(
        reasons=(TRANSACTION_REASON_DAILY_BONUS,), currency=TransactionCurrency.dust, mode="count"
    ),
}


@dataclass(frozen=True)
class QuestDef:
    code: str
    text: str
    metric: str  # ключ в QUEST_METRICS
    target: int
    reward_dust: int
    reward_tickets: int


# Пул из 30 заданий, 3 уровня сложности (по числу в имени кода: _easy/_medium/_hard),
# кроме двух метрик, которые физически не масштабируются под сложность — участие в обмене
# клана (нет смысла требовать больше 1-2 в день) и ежедневный бонус (забрать можно 1 раз
# в сутки в принципе). Игроку, у кого задание невыполнимо сегодня (например, не в клане),
# доступен переролл (см. CLAUDE.md, "Ежедневные задания") — это штатный кейс, не баг.
QUEST_DEFS: tuple[QuestDef, ...] = (
    # --- Крутка: число круток (х1/х10 — 1 действие) ---
    QuestDef("roll_actions_easy", "Сделай 3 крутки", "roll_actions", 3, 25, 0),
    QuestDef("roll_actions_medium", "Сделай 7 круток", "roll_actions", 7, 60, 1),
    QuestDef("roll_actions_hard", "Сделай 15 круток", "roll_actions", 15, 140, 2),
    # --- Крутка: заработанный UBP ---
    QuestDef("roll_ubp_easy", "Заработай 300 UBP от круток", "roll_ubp", 300, 25, 0),
    QuestDef("roll_ubp_medium", "Заработай 1000 UBP от круток", "roll_ubp", 1000, 65, 1),
    QuestDef("roll_ubp_hard", "Заработай 3000 UBP от круток", "roll_ubp", 3000, 150, 2),
    # --- Слияние: число слияний ---
    QuestDef("merge_actions_easy", "Смержи карты 1 раз", "merge_actions", 1, 30, 0),
    QuestDef("merge_actions_medium", "Смержи карты 2 раза", "merge_actions", 2, 70, 1),
    QuestDef("merge_actions_hard", "Смержи карты 4 раза", "merge_actions", 4, 160, 3),
    # --- Слияние: бонусный UBP от слияний ---
    QuestDef("merge_ubp_easy", "Заработай 200 UBP от слияний", "merge_ubp", 200, 30, 0),
    QuestDef("merge_ubp_medium", "Заработай 600 UBP от слияний", "merge_ubp", 600, 70, 1),
    QuestDef("merge_ubp_hard", "Заработай 1500 UBP от слияний", "merge_ubp", 1500, 150, 2),
    # --- Распыление: заработанная пыль ---
    QuestDef("dust_earned_easy", "Получи 40 пыли распылением", "dust_earned", 40, 20, 0),
    QuestDef("dust_earned_medium", "Получи 120 пыли распылением", "dust_earned", 120, 55, 1),
    QuestDef("dust_earned_hard", "Получи 300 пыли распылением", "dust_earned", 300, 130, 2),
    # --- Казино: число заходов ---
    QuestDef("casino_plays_easy", "Сыграй в казино 1 раз", "casino_plays", 1, 25, 0),
    QuestDef("casino_plays_medium", "Сыграй в казино 3 раза", "casino_plays", 3, 60, 1),
    QuestDef("casino_plays_hard", "Сыграй в казино 6 раз", "casino_plays", 6, 140, 2),
    # --- Казино: потраченные коины ---
    QuestDef("casino_coins_spent_easy", "Потрать 15 коинов в казино", "casino_coins_spent", 15, 25, 0),
    QuestDef("casino_coins_spent_medium", "Потрать 60 коинов в казино", "casino_coins_spent", 60, 60, 1),
    QuestDef("casino_coins_spent_hard", "Потрать 150 коинов в казино", "casino_coins_spent", 150, 140, 2),
    # --- Магазин: число покупок тикетов ---
    QuestDef("shop_tickets_easy", "Купи тикеты в магазине 1 раз", "shop_ticket_purchases", 1, 20, 0),
    QuestDef("shop_tickets_medium", "Купи тикеты в магазине 3 раза", "shop_ticket_purchases", 3, 55, 1),
    QuestDef("shop_tickets_hard", "Купи тикеты в магазине 5 раз", "shop_ticket_purchases", 5, 130, 2),
    # --- Магазин: пыль, потраченная на тикеты ---
    QuestDef("shop_dust_spent_easy", "Потрать 20 пыли в магазине", "shop_dust_spent", 20, 20, 0),
    QuestDef("shop_dust_spent_medium", "Потрать 80 пыли в магазине", "shop_dust_spent", 80, 55, 1),
    QuestDef("shop_dust_spent_hard", "Потрать 200 пыли в магазине", "shop_dust_spent", 200, 130, 2),
    # --- Обмен в клане (только 2 уровня — см. комментарий выше пула) ---
    QuestDef("clan_exchange_easy", "Обменяйся ресурсами с кланом 1 раз", "clan_exchange_participation", 1, 25, 0),
    QuestDef("clan_exchange_medium", "Обменяйся ресурсами с кланом 2 раза", "clan_exchange_participation", 2, 70, 1),
    # --- Ежедневный бонус (только 1 уровень — см. комментарий выше пула) ---
    QuestDef("daily_bonus_claim", "Забери ежедневный бонус", "daily_bonus_claims", 1, 25, 0),
)

QUEST_DEFS_BY_CODE: dict[str, QuestDef] = {q.code: q for q in QUEST_DEFS}
