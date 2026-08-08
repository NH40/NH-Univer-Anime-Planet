"""Удаляет одну карточку из БД целиком: саму запись `cards` и ВСЕ её копии из
инвентарей игроков (`user_cards`, все звёзды) — нужно, когда файл карты убран из
assets/cards/ вручную. `seed_cards.py` только апсертит найденные на диске карты и
никогда не удаляет то, что с диска пропало (см. его докстринг), поэтому одного удаления
файла недостаточно — запись в БД и копии у игроков останутся висеть.

`user_cards.card_id` смотрит на `cards.id` через `ondelete="RESTRICT"` (единственная
таблица, ссылающаяся на карточки, см. src/bot/db/models/inventory.py) — удалить саму
карточку, не почистив сначала все её копии у игроков, физически нельзя, Postgres
откажет по FK. Поэтому порядок: сначала user_cards, потом cards, одной транзакцией.

Без --confirm только показывает, что будет удалено (сколько игроков, сколько всего
копий по звёздам) и ничего не меняет — та же осторожность, что и у других необратимых
admin-операций в проекте (см. CLAUDE.md, "Полный сброс БД").

Запуск (внутри контейнера бота или локально с тем же DATABASE_URL):
    python scripts/remove_card.py --universe lookism --id 111 [--confirm]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bot.config.settings import get_settings  # noqa: E402
from bot.db.models.card import Card  # noqa: E402
from bot.db.models.inventory import UserCard  # noqa: E402
from bot.db.session import make_engine, make_session_factory  # noqa: E402

log = logging.getLogger("remove_card")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--universe", required=True, help="Код вселенной, например lookism")
    parser.add_argument(
        "--id", required=True, dest="external_id", help="external_id из имени файла, например 111"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Без флага — только предпросмотр, ничего не меняет"
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    async with session_factory() as session:
        card = (
            await session.execute(
                select(Card).where(Card.universe_code == args.universe, Card.external_id == args.external_id)
            )
        ).scalar_one_or_none()

        if card is None:
            log.error("Карточка не найдена: universe=%s id=%s", args.universe, args.external_id)
            await engine.dispose()
            raise SystemExit(1)

        owners_row = (
            await session.execute(
                select(
                    func.count(func.distinct(UserCard.user_id)),
                    func.coalesce(func.sum(UserCard.quantity), 0),
                ).where(UserCard.card_id == card.id)
            )
        ).one()
        owner_count, copies_total = owners_row

        log.info(
            "Карточка #%d: %s / %s (%d UBP) — %r",
            card.id,
            card.universe_code,
            card.external_id,
            card.base_ubp,
            card.name,
        )
        log.info("У игроков: %d владельцев, %d копий суммарно (все звёзды).", owner_count, copies_total)

        if not args.confirm:
            log.info("Предпросмотр (dry-run) — ничего не удалено. Повторите с --confirm, чтобы применить.")
            await engine.dispose()
            return

        await session.execute(delete(UserCard).where(UserCard.card_id == card.id))
        await session.execute(delete(Card).where(Card.id == card.id))
        await session.commit()
        log.info("Готово: карточка и все её копии у игроков удалены.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
