from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import donate as donate_service
from bot.texts.donate import DONATE_SUCCESS

router = Router(name="payment")

_KOPECKS_PER_RUB = 100

# Единственный рублёвый товар сейчас — донат (см. handlers/donate._send_invoice). Слот
# капа тикетов раньше тоже продавался за рубли через этот хендлер (payload
# "ticket_cap_seasonal:"/"ticket_cap_permanent:") — с 2026-08-17 продаётся за коины в
# магазине коинов (см. services/shop.buy_ticket_cap_with_coins), этот путь диспетчеризации
# больше не нужен.


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    # Инвойс создаём только сами (см. _send_invoice в donate), сумма/валюта в нём уже
    # валидны на момент создания, отдельная проверка "товар ещё в наличии" здесь не нужна.
    # Отвечаем сразу, без похода в БД — важен SLA 10 секунд (см. CLAUDE.md, "Донат").
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, session: AsyncSession) -> None:
    payment = message.successful_payment
    amount_rub = payment.total_amount // _KOPECKS_PER_RUB

    coins = await donate_service.credit_payment(
        session,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        user_id=message.from_user.id,
        amount_rub=amount_rub,
    )
    if coins is None:
        # Повторная доставка апдейта от Telegram — уже начислено раньше, не начисляем второй раз.
        return
    await message.answer(DONATE_SUCCESS.format(coins=coins))
