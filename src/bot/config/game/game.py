"""Игровые числа в одном месте (см. CLAUDE.md, правило 8) — шансы, лимиты, формулы.
Меняя баланс, трогаем только этот файл, а не хендлеры/сервисы."""

from __future__ import annotations

# --- Тикеты (см. CLAUDE.md, "Модель тикетов") ---
TICKET_NATURAL_CAP = 3
# Стартовый баланс нового игрока — сверх капа регена, тот же принцип, что докупка/подарок
# (см. CLAUDE.md: баланс не ограничен сверху, ограничен только пассивный реген).
TICKET_STARTING_COUNT = 15
TICKET_REGEN_INTERVAL_SECONDS = 2 * 60 * 60  # 1 тикет за 2 часа
# Подписка ускоряет пассивный реген вдвое, пока активна (см. CLAUDE.md, "Подписка").
TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED = 60 * 60
ROLL_ONE_COST = 1
ROLL_TEN_COST = 10
ROLL_TEN_COUNT = 10

# --- Подписка (см. CLAUDE.md, "Подписка") ---
SUBSCRIPTION_DAILY_TICKETS = 5
SUBSCRIPTION_DAILY_TICKET_INTERVAL_SECONDS = 24 * 60 * 60

# --- Уведомления (фоновый шедулер, см. services/notify) ---
NOTIFY_ROLL_REMINDER_INTERVAL_SECONDS = 12 * 60 * 60

# --- Шансы по UBP-тирам (фиксированные тиры; см. "Модель начисления UBP" в CLAUDE.md) ---
# Сумма должна быть равна 100 — есть проверка в тестах/скрипте валидации.
TIER_CHANCE_PERCENT: dict[int, float] = {
    6000: 1,
    5000: 4,
    4000: 10,
    3000: 10,
    2000: 25,
    1000: 50,
}

# --- Распыление: пыль за карту 1★ = base_ubp // DUST_DIVISOR (6000 UBP -> 6 пыли, 1000 -> 1) ---
DUST_DIVISOR = 1000

# --- Слияние ---
MERGE_COPIES_REQUIRED = 5
MERGE_MULTIPLIER = 5 * 1.2  # новый UBP = старый UBP * 5 * 1.2 (собрали 5 карт + 20% бонус)

# --- Магазин пыли ---
SHOP_TICKET_PRICE_DUST = 20  # 20 пыли = 1 тикет
SHOP_TICKET_PRESETS = (1, 5, 10)
SHOP_TICKET_MAX_QUANTITY = 1000  # защита от абсурдного ввода в "своё число", не игровой лимит

# --- Ивенты (см. CLAUDE.md, "Ивенты") ---
# Шанс проверяется на КАЖДУЮ выпадающую карту (не на всю крутку x10 разом), пока есть
# активный ивент — не входит в TIER_CHANCE_PERCENT (это отдельная "перебивающая" проверка
# поверх обычного выбора тира, см. services/gacha._roll).
EVENT_CARD_CHANCE = 0.0005  # 0.05%
EVENT_CARD_UBP = 7000  # вне TIER_CHANCE_PERCENT — не участвует в обычной крутке/тир-пикере

# --- Магазин коинов (подтверждено пользователем 2026-08-05) ---
SUBSCRIPTION_PRICE_COINS = 300
SUBSCRIPTION_DURATION_DAYS = 30  # каждая покупка добавляет 30 дней (стакается)

# Разовая покупка на весь текущий сезон — не подписка на дни (см. CLAUDE.md,
# "Сезонный пасс": премиум-ветка открывается навсегда до конца сезона).
BATTLE_PASS_PRICE_COINS = 500

SHOP_COIN_TICKET_PRICE = 5  # 5 коинов = 1 тикет
SHOP_COIN_TICKET_MAX_QUANTITY = 1000

# --- Казино (подтверждено пользователем 2026-08-05: одно правило на все 4 игры) ---
CASINO_ROLL_COST_COINS = 15
# ключ игры -> эмодзи для message.answer_dice(emoji=...); Telegram сам генерирует
# случайное значение на своей стороне — бот не может ни предсказать, ни подделать результат.
CASINO_EMOJI: dict[str, str] = {
    "dice": "🎲",
    "darts": "🎯",
    "football": "⚽",
    "basketball": "🏀",
}
# Масс-крутка — только кубик (так сказал пользователь). Кап — наше инженерное решение:
# каждая крутка это отдельное sendDice-сообщение, без капа масс-крутка на большое число
# заспамит чат и упрётся в rate limit Telegram.
CASINO_MASS_ROLL_MAX = 20

# --- Кланы ---
CLAN_NAME_MIN_LENGTH = 3
CLAN_NAME_MAX_LENGTH = 64
CLAN_DESCRIPTION_MAX_LENGTH = 500
CLAN_WAR_DURATION_HOURS = 6
CLAN_WAR_REWARD_DUST = 200
CLAN_TOP_IMAGE_ELIGIBLE_COUNT = 10  # картинку клана можно ставить только топ-N по UBP всего

# --- Сезонный пасс (подтверждено пользователем 2026-08-05) ---
BATTLE_PASS_MAX_LEVEL = 30
# Стоимость перехода НА уровень N (индекс N-1) в UBP сезона — продиктовано пользователем
# как явные числа, не единая формула: дёшево до 10 уровня (2000 UBP/уровень), скачок на
# 11, дальше растущий шаг сначала до 20 уровня, затем до 30.
BATTLE_PASS_LEVEL_UBP_COST: tuple[int, ...] = (
    1, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000,
    15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000,
    70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000, 160000,
)

# Награды за уровень — формулой (см. CLAUDE.md, правило 8), не статичной таблицей.
# Премиум-ветка ДОПОЛНЯЕТ бесплатную (не заменяет), см. TODO Этап 8.
BATTLE_PASS_FREE_DUST_PER_LEVEL = 10
BATTLE_PASS_PREMIUM_DUST_PER_LEVEL = 20
BATTLE_PASS_MILESTONE_LEVELS = (5, 10, 15, 20, 25, 30)
BATTLE_PASS_FREE_MILESTONE_TICKETS = 1
BATTLE_PASS_PREMIUM_MILESTONE_TICKETS = 2
BATTLE_PASS_COIN_MILESTONE_LEVELS = (10, 20, 30)
BATTLE_PASS_MILESTONE_COINS = 50


def battle_pass_cumulative_ubp(level: int) -> int:
    """Суммарный UBP сезона, нужный чтобы ДОСТИЧЬ уровня `level` (0 -> 0 UBP)."""
    return sum(BATTLE_PASS_LEVEL_UBP_COST[:level])


def battle_pass_level_from_ubp(ubp_season: int) -> int:
    """Текущий уровень пасса по накопленному UBP сезона — уровень считается на лету,
    не хранится отдельной колонкой (как и UBP клана, см. CLAUDE.md, "Кланы")."""
    level = 0
    total = 0
    for cost in BATTLE_PASS_LEVEL_UBP_COST:
        total += cost
        if ubp_season < total:
            break
        level += 1
    return level


def battle_pass_free_reward(level: int) -> tuple[int, int]:
    """(пыль, тикеты) за конкретный уровень бесплатной ветки."""
    dust = level * BATTLE_PASS_FREE_DUST_PER_LEVEL
    tickets = BATTLE_PASS_FREE_MILESTONE_TICKETS if level in BATTLE_PASS_MILESTONE_LEVELS else 0
    return dust, tickets


def battle_pass_premium_reward(level: int) -> tuple[int, int, int]:
    """(пыль, тикеты, коины) за конкретный уровень премиум-ветки — ДОПОЛНИТЕЛЬНО к бесплатной,
    не вместо неё."""
    dust = level * BATTLE_PASS_PREMIUM_DUST_PER_LEVEL
    tickets = BATTLE_PASS_PREMIUM_MILESTONE_TICKETS if level in BATTLE_PASS_MILESTONE_LEVELS else 0
    coins = BATTLE_PASS_MILESTONE_COINS if level in BATTLE_PASS_COIN_MILESTONE_LEVELS else 0
    return dust, tickets, coins


# --- Донат (ЮKassa через Telegram Bot Payments; см. CLAUDE.md, "Донат") ---
DONATE_MIN_RUB = 50
DONATE_MAX_RUB = 50000
DONATE_COINS_PER_RUB = 1  # 1₽ = 1 коин
DONATE_PRESETS_RUB: tuple[int, ...] = (50, 100, 300, 500, 1000, 3000)

# --- Смена сезона (подтверждено пользователем 2026-08-05: коины по местам топ-10 по UBP сезона) ---
# Индекс 0 = 1 место, индекс 9 = 10 место.
SEASON_TOP10_REWARD_COINS: tuple[int, ...] = (1000, 600, 600, 300, 300, 300, 300, 300, 300, 300)

# --- Рефералы (см. CLAUDE.md, "Рефералы") --- Награда рефереру начисляется после ПЕРВОЙ
# крутки приглашённого (не сразу при /start) — анти-абьюз пустыми аккаунтами.
REFERRAL_FIRST_ROLL_REWARD_COINS = 50
REFERRAL_FIRST_ROLL_REWARD_TICKETS = 50
# Доля от суммы доната реферала, начисляемая рефереру (в коинах), пока связь referred_by_id
# не разорвана — округление вниз (см. services/donate.credit_payment).
REFERRAL_DONATE_CUT_PERCENT = 10


def ubp_for_stars(base_ubp: int, stars: int) -> int:
    """UBP карты на уровне `stars` (1★ = base_ubp). Каждая следующая звезда — это одно
    слияние: ×MERGE_MULTIPLIER с округлением НА КАЖДОМ шаге (не единой степенью в конце),
    чтобы значение точно совпадало с тем, что реально накопится по цепочке слияний."""
    value = base_ubp
    for _ in range(stars - 1):
        value = round(value * MERGE_MULTIPLIER)
    return value


def dust_for_stars(base_ubp: int, stars: int) -> int:
    """Пыль за ОДНУ карту уровня `stars` при распылении. Не путать с ubp_for_stars —
    множитель другой. Пользователь явно сказал про смёрженную карту: "можно распылить
    как за 5 повторок" — то есть 2★ (сделанная из 5 копий 1★) распыляется на 5×
    пыли базовой карты, а не на её UBP-эквивалент (который был бы ×6 из-за 20% бонуса
    слияния). Обобщаем на более высокие звёзды тем же множителем 5 за каждый шаг слияния
    (MERGE_COPIES_REQUIRED, а не MERGE_MULTIPLIER)."""
    return (base_ubp // DUST_DIVISOR) * (MERGE_COPIES_REQUIRED ** (stars - 1))


# --- Ежедневный бонус (streak 1-7 дней, см. CLAUDE.md, "Ежедневный бонус") ---
DAILY_BONUS_MAX_STREAK = 7
# (пыль, тикеты) по дню серии — индекс 0 = день 1. Растущая шкала, день 7 — самый ценный
# (~5 тикетов, как просил пользователь) — числа не продиктованы, посчитаны для баланса
# (масштаб пыли ориентирован на SHOP_TICKET_PRICE_DUST = 20 пыли/тикет).
DAILY_BONUS_REWARDS: tuple[tuple[int, int], ...] = (
    (20, 0),
    (30, 0),
    (40, 1),
    (60, 1),
    (80, 2),
    (100, 2),
    (150, 5),
)


def daily_bonus_reward(day: int) -> tuple[int, int]:
    """(пыль, тикеты) за день `day` серии (1..DAILY_BONUS_MAX_STREAK)."""
    return DAILY_BONUS_REWARDS[day - 1]
