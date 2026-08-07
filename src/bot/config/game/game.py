"""Игровые числа в одном месте (см. CLAUDE.md, правило 8) — шансы, лимиты, формулы.
Меняя баланс, трогаем только этот файл, а не хендлеры/сервисы."""

from __future__ import annotations

import random

# --- Тикеты (см. CLAUDE.md, "Модель тикетов") ---
TICKET_NATURAL_CAP = 3
# Стартовый баланс нового игрока — сверх капа регена, тот же принцип, что докупка/подарок
# (см. CLAUDE.md: баланс не ограничен сверху, ограничен только пассивный реген).
TICKET_STARTING_COUNT = 15
TICKET_REGEN_INTERVAL_SECONDS = 2 * 60 * 60  # 1 тикет за 2 часа
# Подписка ускоряет пассивный реген вдвое, пока активна (см. CLAUDE.md, "Подписка").
TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED = 60 * 60
# Крутка только по одной карте за раз (намеренно, подтверждено пользователем 2026-08-06:
# x10 убрана — цепочка одиночных круток с кнопкой "Крутить ещё" на экране результата
# затягивает сильнее, чем пачка результатов разом).
ROLL_ONE_COST = 1

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

# --- Сезонный пасс: 500-уровневый бесконечный цикл (переработано 2026-08-08 по запросу
# пользователя — предыдущая 30-уровневая модель с ручной таблицей стоимости признана
# "слишком большой", см. CLAUDE.md, "Сезонный пасс: 500 циклических уровней").
#
# Стоимость перехода на уровень — от АБСОЛЮТНОГО номера уровня (не циклится): линейная
# рампа от BATTLE_PASS_COST_START (уровень 1) до BATTLE_PASS_COST_ENDLESS (уровень 500),
# дальше — плоская BATTLE_PASS_COST_ENDLESS навсегда (без разрыва в точке 500, т.к. рампа
# и так достигает этого значения к этому уровню). Подтверждено пользователем: "бесконечный
# цикл, 30000 UBP/уровень навсегда" после первого прохождения 500 уровней.
BATTLE_PASS_CYCLE_LEVELS = 500
BATTLE_PASS_COST_START = 300
BATTLE_PASS_COST_ENDLESS = 30000


def battle_pass_level_cost(level: int) -> int:
    """UBP-стоимость перехода С уровня level-1 НА уровень level (level >= 1)."""
    if level >= BATTLE_PASS_CYCLE_LEVELS:
        return BATTLE_PASS_COST_ENDLESS
    return round(
        BATTLE_PASS_COST_START
        + (BATTLE_PASS_COST_ENDLESS - BATTLE_PASS_COST_START) * (level - 1) / (BATTLE_PASS_CYCLE_LEVELS - 1)
    )


# Награды циклятся каждые BATTLE_PASS_CYCLE_LEVELS уровней (см. battle_pass_free_reward) —
# формула берёт ПОЗИЦИЮ в цикле, не абсолютный уровень. НЕ РАСТУТ с уровнем (изменено
# 2026-08-08 по запросу пользователя — исходная растущая формула с минор/мажор-чекпоинтами
# снова показалась "слишком большой" на дальних уровнях цикла): каждый уровень цикла даёт
# ЛИБО немного тикетов, ЛИБО немного пыли — выбор и величина детерминированы от позиции
# (`_battle_pass_roll`, seed = pos), поэтому один и тот же уровень всегда даёт одну и ту же
# награду (и в ленте-превью, и при реальном клейме), просто "вперемешку", а не по формуле
# от номера уровня. Премиум-ветка бросает свой НЕЗАВИСИМЫЙ ролл (другой seed) поверх
# бесплатной — ДОПОЛНЯЕТ, не заменяет.
BATTLE_PASS_TICKET_MIN = 1
BATTLE_PASS_TICKET_MAX = 3
BATTLE_PASS_DUST_MIN = 10
BATTLE_PASS_DUST_MAX = 50
_BATTLE_PASS_PREMIUM_SEED_OFFSET = 10_000  # разный seed от free — независимый ролл
BATTLE_PASS_COIN_MILESTONE_MOD = 50  # только премиум-ветка, каждый 50-й уровень цикла
BATTLE_PASS_MILESTONE_COINS = 15


def _battle_pass_roll(seed: int) -> tuple[int, int]:
    """(пыль, тикеты) — детерминированный по seed выбор 50/50: либо
    BATTLE_PASS_TICKET_MIN..MAX тикетов, либо BATTLE_PASS_DUST_MIN..MAX пыли. Один и тот же
    seed всегда даёт один и тот же результат (не хранится в БД, пересчитывается на лету)."""
    rng = random.Random(seed)
    if rng.random() < 0.5:
        return 0, rng.randint(BATTLE_PASS_TICKET_MIN, BATTLE_PASS_TICKET_MAX)
    return rng.randint(BATTLE_PASS_DUST_MIN, BATTLE_PASS_DUST_MAX), 0


def battle_pass_cumulative(level: int) -> int:
    """Суммарный прогресс (UBP-эквивалент), нужный чтобы ДОСТИЧЬ уровня `level` (0 -> 0).
    За пределами первого прохождения (level > 500) считается в O(1), не циклом."""
    if level <= BATTLE_PASS_CYCLE_LEVELS:
        return sum(battle_pass_level_cost(lvl) for lvl in range(1, level + 1))
    base = sum(battle_pass_level_cost(lvl) for lvl in range(1, BATTLE_PASS_CYCLE_LEVELS + 1))
    return base + (level - BATTLE_PASS_CYCLE_LEVELS) * BATTLE_PASS_COST_ENDLESS


def battle_pass_level_from_progress(progress: int) -> int:
    """Текущий уровень пасса по накопленному прогрессу (см. `BattlePass.progress` —
    ОТДЕЛЬНЫЙ от `User.ubp_season` счётчик, см. CLAUDE.md). Уровни > 500 считаются в O(1)."""
    cap_total = battle_pass_cumulative(BATTLE_PASS_CYCLE_LEVELS)
    if progress >= cap_total:
        return BATTLE_PASS_CYCLE_LEVELS + (progress - cap_total) // BATTLE_PASS_COST_ENDLESS

    level = 0
    total = 0
    for lvl in range(1, BATTLE_PASS_CYCLE_LEVELS + 1):
        total += battle_pass_level_cost(lvl)
        if progress < total:
            break
        level += 1
    return level


def battle_pass_free_reward(level: int) -> tuple[int, int]:
    """(пыль, тикеты) за конкретный АБСОЛЮТНЫЙ уровень бесплатной ветки — награда циклится
    по позиции внутри BATTLE_PASS_CYCLE_LEVELS, не растёт с уровнем (см. комментарий выше)."""
    pos = ((level - 1) % BATTLE_PASS_CYCLE_LEVELS) + 1
    return _battle_pass_roll(pos)


def battle_pass_premium_reward(level: int) -> tuple[int, int, int]:
    """(пыль, тикеты, коины) за конкретный уровень премиум-ветки — ДОПОЛНИТЕЛЬНО к
    бесплатной (независимый ролл, другой seed), плюс коины на каждом
    BATTLE_PASS_COIN_MILESTONE_MOD-м уровне цикла."""
    pos = ((level - 1) % BATTLE_PASS_CYCLE_LEVELS) + 1
    dust, tickets = _battle_pass_roll(pos + _BATTLE_PASS_PREMIUM_SEED_OFFSET)
    coins = BATTLE_PASS_MILESTONE_COINS if pos % BATTLE_PASS_COIN_MILESTONE_MOD == 0 else 0
    return dust, tickets, coins


# Дневной буст набора `BattlePass.progress` (подтверждено пользователем 2026-08-08): первые
# BATTLE_PASS_BOOST_TIER_LEVELS[0] уровней прогресса за день дают ×BATTLE_PASS_BOOST_TIER_MULTIPLIERS[0]
# к реальному начисленному UBP, следующие [1] уровней — ×[1], следующие [2] — ×[2], дальше —
# без буста (×1). Считается в "уровнях прогресса", использованных СЕГОДНЯ (см.
# services/battle_pass.add_progress) — НЕ влияет на User.ubp_season (лидерборд/войны кланов
# остаются на настоящем UBP, см. CLAUDE.md).
BATTLE_PASS_BOOST_TIER_LEVELS: tuple[int, ...] = (5, 10, 20)
BATTLE_PASS_BOOST_TIER_MULTIPLIERS: tuple[int, ...] = (10, 5, 2)


def battle_pass_boost_multiplier(levels_used_today: int) -> int:
    """Множитель дневного буста по тому, сколько boosted-уровней прогресса уже использовано
    сегодня — 1 (без буста), если дневная квота исчерпана."""
    for threshold, multiplier in zip(BATTLE_PASS_BOOST_TIER_LEVELS, BATTLE_PASS_BOOST_TIER_MULTIPLIERS):
        if levels_used_today < threshold:
            return multiplier
    return 1


# --- Донат (ЮKassa через Telegram Bot Payments; см. CLAUDE.md, "Донат") ---
DONATE_MIN_RUB = 50
DONATE_MAX_RUB = 50000
DONATE_COINS_PER_RUB = 1  # 1₽ = 1 коин
DONATE_PRESETS_RUB: tuple[int, ...] = (50, 100, 300, 500, 1000, 3000)

# --- Смена сезона (подтверждено пользователем 2026-08-05: коины по местам топ-10 по UBP сезона) ---
# Индекс 0 = 1 место, индекс 9 = 10 место.
SEASON_TOP10_REWARD_COINS: tuple[int, ...] = (1000, 600, 600, 300, 300, 300, 300, 300, 300, 300)

# --- Рефералы (см. CLAUDE.md, "Рефералы") --- Награда рефереру начисляется после того, как
# приглашённый сделает REFERRAL_ROLL_THRESHOLD круток (не сразу при /start и не после
# первой — порог подняли 2026-08-06, чтобы не давать награду за пустые/брошенные аккаунты).
REFERRAL_ROLL_THRESHOLD = 30
REFERRAL_ROLL_REWARD_COINS = 50
REFERRAL_ROLL_REWARD_TICKETS = 50
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
