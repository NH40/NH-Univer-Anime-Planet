from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.enums import PaymentItemKind
from bot.services import donate as donate_service
from bot.services import shop as shop_service
from bot.texts.donate import DONATE_SUCCESS
from bot.texts.shop import TICKET_CAP_PURCHASE_SUCCESS

router = Router(name="payment")

_KOPECKS_PER_RUB = 100

# Первый сегмент payload (см. handlers/donate._send_invoice,
# handlers/shop.cb_buy_ticket_cap_seasonal/permanent) — единая точка диспетчеризации
# успешного платежа по товару. Раньше этот хендлер жил в handlers/donate и безусловно
# кредитовал коины — с появлением второго рублёвого товара (слот капа тикетов, см.
# CLAUDE.md) стало необходимо реально смотреть, что было куплено.
_KIND_TICKET_CAP_SEASONAL = "ticket_cap_seasonal"
_KIND_TICKET_CAP_PERMANENT = "ticket_cap_permanent"


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    # Инвойс создаём только сами (см. _send_invoice в donate/shop) — сумма/валюта в нём уже
    # валидны на момент создания, отдельная проверка "товар ещё в наличии" здесь не нужна.
    # Отвечаем сразу, без похода в БД — важен SLA 10 секунд (см. CLAUDE.md, "Донат").
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, session: AsyncSession) -> None:
    payment = message.successful_payment
    amount_rub = payment.total_amount // _KOPECKS_PER_RUB
    kind = payment.invoice_payload.split(":", 1)[0]

    if kind in (_KIND_TICKET_CAP_SEASONAL, _KIND_TICKET_CAP_PERMANENT):
        item_kind = (
            PaymentItemKind.ticket_cap_seasonal if kind == _KIND_TICKET_CAP_SEASONAL else PaymentItemKind.ticket_cap_permanent
        )
        new_bonus = await shop_service.credit_ticket_cap_purchase(
            session,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            user_id=message.from_user.id,
            amount_rub=amount_rub,
            kind=item_kind,
        )
        if new_bonus is not None:
            await message.answer(TICKET_CAP_PURCHASE_SUCCESS.format(bonus=new_bonus))
        return

    # payload "donate:<сумма>" (или неизвестный/устаревший префикс) — прежнее поведение по
    # умолчанию: кредитуем коины.
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
