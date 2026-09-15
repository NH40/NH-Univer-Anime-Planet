"""Сканирует assets/cards/<universe>/<ubp>UBP/<id>_<Name>.<ext> и регистрирует/обновляет
карточки в БД (таблицы universes, cards). Безопасно перезапускать — используется upsert,
повторный запуск подхватит переименования/новые файлы и не создаст дублей.

Описания карт (необязательно) — один файл descriptions.csv на папку (обычную UBP-папку,
или celestial/divine — см. ниже), колонки "id,description" (id — то же число, что в имени
файла карты, ведущие нули не важны). Значения с запятой берите в кавычки (обычный CSV).
Карта, для которой в файле нет строки, останется без описания.

Небесные и божественные карты (см. CLAUDE.md, "Небесные карты") — два зарезервированных
имени папки ВНУТРИ каждой вселенной, вместо "<ubp>UBP":
    assets/cards/<universe>/celestial/<id>_<Name>.<ext> — ровно CELESTIAL_CARD_COUNT (10)
        штук на весь бот суммарно (по несколько на разные вселенные, как решит админ).
        base_ubp всегда CELESTIAL_CARD_BASE_UBP, id/имя — любые, не пересекаются между
        вселенными по смыслу (просто уникальные внутри своей папки).
    assets/cards/<universe>/divine/<id>_<Name>.<ext> — по одной "обычной" (полный сбор
        ростера вселенной) карте на вселенную, ЛЮБОЙ id, КРОМЕ:
          - id=1000 — единственная на весь бот, за одновременное владение ВСЕМИ небесными;
          - id=999  — единственная на весь бот, псевдо-божественная (слабее 1000, за
            владение всеми небесными КОГДА-ЛИБО, не обязательно одновременно).
        Обе карты 1000/999 физически кладутся в папку divine/ ЛЮБОЙ одной вселенной на
        выбор админа (просто как место хранения картинки) — они не привязаны к конкретной
        вселенной по смыслу.
Каждая из этих папок тоже может иметь свой descriptions.csv. Скрипт предупредит (не
заблокирует запуск), если количество небесных/1000/999 карт не совпадает с ожидаемым —
это ожидаемое переходное состояние, пока админ заполняет данные постепенно.

Запуск (внутри контейнера бота или локально с тем же DATABASE_URL):
    python scripts/seed_cards.py [--assets-dir assets/cards] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bot.config.event import EVENT_DEFS  # noqa: E402
from bot.config.game import (  # noqa: E402
    CELESTIAL_CARD_BASE_UBP,
    CELESTIAL_CARD_COUNT,
    DIVINE_CARD_BASE_UBP,
    DIVINE_PSEUDO_CARD_BASE_UBP,
    TIER_CHANCE_PERCENT,
)
from bot.config.settings import get_settings  # noqa: E402
from bot.db.models.card import Card  # noqa: E402
from bot.db.models.universe import Universe  # noqa: E402
from bot.db.session import make_engine, make_session_factory  # noqa: E402

# Коды вселенных, зарезервированные под ивенты (см. CLAUDE.md, "Ивенты") — семантика
# отличается от обычных вселенных двумя вещами ниже: другой источник заголовка и
# исключение из проверки полноты тиров (у них есть только 7000 UBP, не все 6 обычных).
EVENT_UNIVERSE_TITLES = {d.universe_code: d.title for d in EVENT_DEFS}

log = logging.getLogger("seed_cards")

UBP_DIR_RE = re.compile(r"^(\d+)UBP$", re.IGNORECASE)
CARD_FILE_RE = re.compile(r"^(?P<id>\d+)_(?P<name>.+)\.(?P<ext>png|jpg|jpeg|webp)$", re.IGNORECASE)
# Вставляет пробел на границах слипшегося PascalCase из имени файла:
#  1) "строчная/цифра -> заглавная" (JongGunSmile -> Jong Gun Smile);
#  2) "заглавная -> заглавная+строчная", т.е. конец акронима перед новым словом
#     (JongGunVSGooKim -> ...VS Goo..., а не ...VSGoo...). Подряд заглавные САМИ ПО
#     СЕБЕ (акронимы вроде TUI) не разбиваются — только когда следом идёт новое слово.
_PASCAL_CASE_BOUNDARY_RE = re.compile(
    r"(?<=[a-zа-я0-9])(?=[A-ZА-Я])" r"|(?<=[A-ZА-Я])(?=[A-ZА-Я][a-zа-я])"
)

# Человекочитаемые названия для известных вселенных; для новых папок — Title Case по умолчанию.
KNOWN_UNIVERSE_TITLES = {
    "onepiece": "One Piece",
    "lookism": "Lookism",
    "genshin": "Genshin Impact",
}

DESCRIPTIONS_FILENAME = "descriptions.csv"

# Небесные/божественные карты (см. CLAUDE.md, "Небесные карты") — не папки-тиры вида
# "<n>UBP", а два зарезервированных имени папки внутри каждой вселенной, со своим
# descriptions.csv по тому же формату, что и обычные карты. Не участвуют в проверке
# полноты тиров (check_tier_completeness) и не попадают под предупреждение "тир не входит
# в TIER_CHANCE_PERCENT" — у них своя, отдельная логика ниже, не общий UBP_DIR_RE проход.
CELESTIAL_DIR_NAME = "celestial"
DIVINE_DIR_NAME = "divine"
# external_id, зарезервированные пользователем под особые подтипы божественной карты
# (2026-09-15) — любой другой id в папке divine/ трактуется как обычный "000"-вариант
# (полный сбор ростера СВОЕЙ вселенной), без отдельной метки в имени файла/CSV.
DIVINE_GLOBAL_EXTERNAL_ID = "1000"
DIVINE_PSEUDO_EXTERNAL_ID = "999"


@dataclass
class ParsedCard:
    universe_code: str
    external_id: str
    name: str
    base_ubp: int
    image_path: str  # относительно assets-dir, например onepiece/6000UBP/001_Name.png
    description: str | None = None
    is_celestial: bool = False
    is_divine: bool = False
    is_divine_global: bool = False
    is_divine_pseudo: bool = False


def _clean_name(raw: str) -> str:
    name = raw.replace("_", " ").strip()
    name = _PASCAL_CASE_BOUNDARY_RE.sub(" ", name)
    return re.sub(r" {2,}", " ", name).strip()


def load_descriptions(universe_dir: Path) -> dict[str, str]:
    """Читает <universe_dir>/descriptions.csv (колонки "id,description"), если он есть.
    Ключ — id, приведённый к int и обратно к строке (чтобы "01" и "1" совпадали с любым
    написанием id в имени файла карты). CSV — единственный источник правды: карта, у
    которой в файле нет строки, останется без описания, даже если раньше было другое."""
    path = universe_dir / DESCRIPTIONS_FILENAME
    if not path.is_file():
        return {}

    descriptions: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "id" not in reader.fieldnames or "description" not in reader.fieldnames:
            log.warning("%s: ожидались колонки 'id,description' в первой строке — файл пропущен", path)
            return {}
        for row in reader:
            raw_id = (row.get("id") or "").strip()
            text = (row.get("description") or "").strip()
            if not raw_id.isdigit() or not text:
                continue
            descriptions[str(int(raw_id))] = text
    return descriptions


def scan_assets(assets_dir: Path) -> tuple[dict[str, str], list[ParsedCard]]:
    universes: dict[str, str] = {}
    cards: list[ParsedCard] = []

    for universe_dir in sorted(p for p in assets_dir.iterdir() if p.is_dir()):
        code = universe_dir.name
        universes[code] = EVENT_UNIVERSE_TITLES.get(
            code, KNOWN_UNIVERSE_TITLES.get(code, code.replace("_", " ").title())
        )
        descriptions = load_descriptions(universe_dir)

        for ubp_dir in sorted(p for p in universe_dir.iterdir() if p.is_dir()):
            if ubp_dir.name.lower() in (CELESTIAL_DIR_NAME, DIVINE_DIR_NAME):
                continue  # разбираются отдельно ниже, не общим UBP-тир проходом

            match = UBP_DIR_RE.match(ubp_dir.name)
            if not match:
                log.warning("Пропускаю папку с непонятным форматом UBP: %s", ubp_dir)
                continue
            base_ubp = int(match.group(1))
            if base_ubp not in TIER_CHANCE_PERCENT:
                log.warning(
                    "Тир %d UBP (%s) не входит в фиксированную таблицу шансов %s — карты "
                    "оттуда будут зарегистрированы в БД, но НЕ будут участвовать в крутке.",
                    base_ubp,
                    ubp_dir,
                    sorted(TIER_CHANCE_PERCENT, reverse=True),
                )

            for file in sorted(p for p in ubp_dir.iterdir() if p.is_file()):
                file_match = CARD_FILE_RE.match(file.name)
                if not file_match:
                    log.warning("Пропускаю файл с непонятным именем: %s", file)
                    continue

                card_id = file_match.group("id")
                cards.append(
                    ParsedCard(
                        universe_code=code,
                        external_id=card_id,
                        name=_clean_name(file_match.group("name")),
                        base_ubp=base_ubp,
                        image_path=str(file.relative_to(assets_dir)).replace("\\", "/"),
                        description=descriptions.get(str(int(card_id))),
                    )
                )

        cards.extend(_scan_relic_dir(assets_dir, universe_dir, code, CELESTIAL_DIR_NAME))
        cards.extend(_scan_relic_dir(assets_dir, universe_dir, code, DIVINE_DIR_NAME))

    return universes, cards


def _scan_relic_dir(assets_dir: Path, universe_dir: Path, universe_code: str, dir_name: str) -> list[ParsedCard]:
    """Небесные (`celestial/`) или божественные (`divine/`) карты этой вселенной (см.
    CLAUDE.md, "Небесные карты") — своя папка со своим descriptions.csv (тот же формат,
    что у обычных карт), но фиксированный base_ubp из config/game (не из имени папки) и
    отдельные флаги на Card вместо участия в обычном тир-пикере."""
    relic_dir = next((p for p in universe_dir.iterdir() if p.is_dir() and p.name.lower() == dir_name), None)
    if relic_dir is None:
        return []

    is_celestial = dir_name == CELESTIAL_DIR_NAME
    base_ubp = CELESTIAL_CARD_BASE_UBP if is_celestial else DIVINE_CARD_BASE_UBP
    descriptions = load_descriptions(relic_dir)

    cards: list[ParsedCard] = []
    for file in sorted(p for p in relic_dir.iterdir() if p.is_file() and p.name != DESCRIPTIONS_FILENAME):
        file_match = CARD_FILE_RE.match(file.name)
        if not file_match:
            log.warning("Пропускаю файл с непонятным именем: %s", file)
            continue

        card_id = file_match.group("id")
        is_divine_global = not is_celestial and card_id == DIVINE_GLOBAL_EXTERNAL_ID
        is_divine_pseudo = not is_celestial and card_id == DIVINE_PSEUDO_EXTERNAL_ID
        cards.append(
            ParsedCard(
                universe_code=universe_code,
                external_id=card_id,
                name=_clean_name(file_match.group("name")),
                base_ubp=DIVINE_PSEUDO_CARD_BASE_UBP if is_divine_pseudo else base_ubp,
                image_path=str(file.relative_to(assets_dir)).replace("\\", "/"),
                description=descriptions.get(str(int(card_id))),
                is_celestial=is_celestial,
                is_divine=not is_celestial,
                is_divine_global=is_divine_global or is_divine_pseudo,
                is_divine_pseudo=is_divine_pseudo,
            )
        )
    return cards


def check_tier_completeness(universes: dict[str, str], cards: list[ParsedCard]) -> bool:
    """По решению пользователя (2026-08-03): пустой тир UBP для вселенной — это ошибка
    данных, а не повод перераспределять шанс на лету. Крутка сама блокируется на рантайме
    (UniverseNotReadyError), но лучше поймать это здесь, при загрузке датасета.
    Возвращает True, если все вселенные полностью укомплектованы."""
    ok = True
    for universe_code in universes:
        if universe_code in EVENT_UNIVERSE_TITLES:
            # Ивентовые вселенные не участвуют в обычной крутке по тирам (см. CLAUDE.md,
            # "Ивенты") — у них ожидаемо только 7000 UBP, полнота TIER_CHANCE_PERCENT
            # для них не проверяется.
            continue
        present_tiers = {c.base_ubp for c in cards if c.universe_code == universe_code}
        missing = sorted((t for t in TIER_CHANCE_PERCENT if t not in present_tiers), reverse=True)
        if missing:
            ok = False
            log.warning(
                "ВСЕЛЕННАЯ НЕ ГОТОВА К КРУТКЕ: '%s' — нет ни одной карты в тире(ах) %s UBP. "
                "Крутка для этой вселенной будет заблокирована, пока не добавите карты.",
                universe_code,
                missing,
            )
    return ok


def check_relic_completeness(cards: list[ParsedCard]) -> None:
    """Небесные/божественные карты (см. CLAUDE.md, "Небесные карты") — не блокирует крутку
    (в отличие от check_tier_completeness, у этих карт нет обязательного минимума для
    штатной работы бота), только предупреждает о несоответствии ожидаемому количеству —
    админ заполняет эти карты вручную и постепенно, по одной."""
    celestial_count = sum(1 for c in cards if c.is_celestial)
    if celestial_count != CELESTIAL_CARD_COUNT:
        log.warning(
            "Небесных карт найдено %d, ожидается ровно %d (CELESTIAL_CARD_COUNT) — "
            "остальные ещё не добавлены в assets/cards/<вселенная>/celestial/.",
            celestial_count,
            CELESTIAL_CARD_COUNT,
        )

    global_count = sum(1 for c in cards if c.is_divine_global and not c.is_divine_pseudo)
    pseudo_count = sum(1 for c in cards if c.is_divine_pseudo)
    if global_count != 1:
        log.warning(
            "Найдено %d карт с id=%s в папках divine/ (ожидается ровно 1 — единственная "
            "\"1000\"-божественная на весь бот).",
            global_count,
            DIVINE_GLOBAL_EXTERNAL_ID,
        )
    if pseudo_count != 1:
        log.warning(
            "Найдено %d карт с id=%s в папках divine/ (ожидается ровно 1 — единственная "
            "псевдо-божественная на весь бот).",
            pseudo_count,
            DIVINE_PSEUDO_EXTERNAL_ID,
        )


async def apply(universes: dict[str, str], cards: list[ParsedCard], *, dry_run: bool) -> None:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    async with session_factory() as session:
        for code, title in universes.items():
            is_event = code in EVENT_UNIVERSE_TITLES
            stmt = (
                pg_insert(Universe)
                .values(code=code, title=title, is_event=is_event)
                .on_conflict_do_update(index_elements=[Universe.code], set_={"title": title, "is_event": is_event})
            )
            if not dry_run:
                await session.execute(stmt)

        for card in cards:
            stmt = (
                pg_insert(Card)
                .values(
                    universe_code=card.universe_code,
                    external_id=card.external_id,
                    name=card.name,
                    base_ubp=card.base_ubp,
                    image_path=card.image_path,
                    description=card.description,
                    is_celestial=card.is_celestial,
                    is_divine=card.is_divine,
                    is_divine_global=card.is_divine_global,
                    is_divine_pseudo=card.is_divine_pseudo,
                )
                .on_conflict_do_update(
                    index_elements=[Card.universe_code, Card.external_id],
                    set_={
                        "name": card.name,
                        "base_ubp": card.base_ubp,
                        "image_path": card.image_path,
                        "description": card.description,
                        "is_celestial": card.is_celestial,
                        "is_divine": card.is_divine,
                        "is_divine_global": card.is_divine_global,
                        "is_divine_pseudo": card.is_divine_pseudo,
                    },
                )
            )
            if not dry_run:
                await session.execute(stmt)

        if not dry_run:
            await session.commit()

    await engine.dispose()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", default="assets/cards")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет сделано")
    args = parser.parse_args()

    assets_dir = Path(args.assets_dir)
    if not assets_dir.is_dir():
        log.error("Директория не найдена: %s", assets_dir)
        raise SystemExit(1)

    universes, cards = scan_assets(assets_dir)
    log.info("Найдено вселенных: %d, карточек: %d", len(universes), len(cards))
    for u_code, u_title in universes.items():
        log.info("  вселенная: %s (%s)", u_code, u_title)

    check_tier_completeness(universes, cards)
    check_relic_completeness(cards)

    await apply(universes, cards, dry_run=args.dry_run)
    log.info("Готово%s.", " (dry-run, ничего не записано)" if args.dry_run else "")


if __name__ == "__main__":
    asyncio.run(main())
