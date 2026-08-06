from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventDef:
    code: str
    title: str
    universe_code: str


# Статичный список из 2 заготовок ивентов (подтверждено пользователем 2026-08-06) — не
# таблица в БД сама по себе является источником правды о том, КАКИЕ ивенты вообще бывают
# (та хранит только is_active и служебные поля, см. db/models/event.py), а этот список: он
# определяет, что видно в /admin, даже если под ивент ещё не залиты карточки в assets/cards
# (universe_code тогда просто не существует как строка в `universes` — крутка и коллекция
# для него естественно пустуют, см. services/gacha, CLAUDE.md "Ивенты"). Пока реально
# доступна только "лукизм" — под "хэллоуин" карточек ещё нет, но переключатель уже готов:
# как только появится assets/cards/event_halloween/... и seed_cards.py его подхватит,
# ивент заработает без единой правки кода.
EVENT_DEFS: tuple[EventDef, ...] = (
    EventDef(code="lookism_battle_planet", title="Лукизм Баттл Планет", universe_code="event_lookism"),
    EventDef(code="halloween", title="Хэллоуин", universe_code="event_halloween"),
)

EVENT_DEFS_BY_CODE: dict[str, EventDef] = {d.code: d for d in EVENT_DEFS}
