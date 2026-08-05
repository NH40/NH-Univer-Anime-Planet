"""Сканирует assets/cards/<universe>/<ubp>UBP/<id>_<Name>.<ext> и регистрирует/обновляет
карточки в БД (таблицы universes, cards). Безопасно перезапускать — используется upsert,
повторный запуск подхватит переименования/новые файлы и не создаст дублей.

Запуск (внутри контейнера бота или локально с тем же DATABASE_URL):
    python scripts/seed_cards.py [--assets-dir assets/cards] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bot.config.game import TIER_CHANCE_PERCENT  # noqa: E402
from bot.config.settings import get_settings  # noqa: E402
from bot.db.models.card import Card  # noqa: E402
from bot.db.models.universe import Universe  # noqa: E402
from bot.db.session import make_engine, make_session_factory  # noqa: E402

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


@dataclass
class ParsedCard:
    universe_code: str
    external_id: str
    name: str
    base_ubp: int
    image_path: str  # относительно assets-dir, например onepiece/6000UBP/001_Name.png


def scan_assets(assets_dir: Path) -> tuple[dict[str, str], list[ParsedCard]]:
    universes: dict[str, str] = {}
    cards: list[ParsedCard] = []

    for universe_dir in sorted(p for p in assets_dir.iterdir() if p.is_dir()):
        code = universe_dir.name
        universes[code] = KNOWN_UNIVERSE_TITLES.get(code, code.replace("_", " ").title())

        for ubp_dir in sorted(p for p in universe_dir.iterdir() if p.is_dir()):
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

                raw_name = file_match.group("name").replace("_", " ").strip()
                name = _PASCAL_CASE_BOUNDARY_RE.sub(" ", raw_name)
                name = re.sub(r" {2,}", " ", name).strip()
                cards.append(
                    ParsedCard(
                        universe_code=code,
                        external_id=file_match.group("id"),
                        name=name,
                        base_ubp=base_ubp,
                        image_path=str(file.relative_to(assets_dir)).replace("\\", "/"),
                    )
                )

    return universes, cards


def check_tier_completeness(universes: dict[str, str], cards: list[ParsedCard]) -> bool:
    """По решению пользователя (2026-08-03): пустой тир UBP для вселенной — это ошибка
    данных, а не повод перераспределять шанс на лету. Крутка сама блокируется на рантайме
    (UniverseNotReadyError), но лучше поймать это здесь, при загрузке датасета.
    Возвращает True, если все вселенные полностью укомплектованы."""
    ok = True
    for universe_code in universes:
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


async def apply(universes: dict[str, str], cards: list[ParsedCard], *, dry_run: bool) -> None:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    async with session_factory() as session:
        for code, title in universes.items():
            stmt = (
                pg_insert(Universe)
                .values(code=code, title=title)
                .on_conflict_do_update(index_elements=[Universe.code], set_={"title": title})
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
                )
                .on_conflict_do_update(
                    index_elements=[Card.universe_code, Card.external_id],
                    set_={"name": card.name, "base_ubp": card.base_ubp, "image_path": card.image_path},
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

    await apply(universes, cards, dry_run=args.dry_run)
    log.info("Готово%s.", " (dry-run, ничего не записано)" if args.dry_run else "")


if __name__ == "__main__":
    asyncio.run(main())
