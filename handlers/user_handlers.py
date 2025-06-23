import logging
from datetime import datetime
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation

from services.database import db
from keyboards.inline import (
    get_mode_selection_keyboard, 
    get_buyer_discount_keyboard, 
    get_confirmation_keyboard,
    get_report_keyboard
)
from services.quotes import get_cbr_usd_rate, get_moex_usd_rate, get_moex_gold_rub_rate
from services.calculator import calculate_final_deal, OUNCE_IN_GRAMS
from utils.state import Calculation
from config import settings

router = Router()

@router.message.middleware()
@router.callback_query.middleware()
async def auth_middleware(handler, event, data):
    if not await db.is_user_allowed(event.from_user.id):
        if isinstance(event, types.Message): await event.answer("⛔️ Доступ запрещен.")
        elif isinstance(event, types.CallbackQuery): await event.answer("⛔️ Доступ запрещен.", show_alert=True)
        return
    return await handler(event, data)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Здравствуйте! Выберите режим расчета:", reply_markup=get_mode_selection_keyboard())

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Текущий расчет отменен. Чтобы начать новый, нажмите /start")

@router.callback_query(F.data == "cancel_calculation")
async def cancel_calculation(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Расчет отменен. Чтобы начать заново, введите /start")
    await callback.answer()

@router.callback_query(F.data.startswith("set_mode_"))
async def set_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[-1]
    await state.update_data(mode=mode)
    await callback.message.edit_text("Введите вес партии в кг (например, `12.5`):")
    await state.set_state(Calculation.weight)
    await callback.answer()

@router.message(Calculation.weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        value = message.text.replace(',', '.').strip()
        Decimal(value)
        await state.update_data(weight=value)
        await message.answer("⏳ Получаю базовую цену с MOEX...")
        moex_usd_rate = await get_moex_usd_rate()
        moex_gold_rub_gram = await get_moex_gold_rub_rate()
        if not moex_usd_rate or not moex_gold_rub_gram:
            await message.answer("❌ Не удалось получить котировки с MOEX. Попробуйте позже.")
            await state.clear()
            return
        base_supplier_price_usd = (Decimal(str(moex_gold_rub_gram)) * OUNCE_IN_GRAMS) / Decimal(str(moex_usd_rate))
        await state.update_data(
            base_supplier_price_usd=str(base_supplier_price_usd.quantize(Decimal("0.01"))),
            moex_usd_rate=str(moex_usd_rate),
            moex_gold_rub_gram=str(moex_gold_rub_gram)
        )
        await message.answer(
            f"Базовая цена поставщика (MOEX): **${base_supplier_price_usd.quantize(Decimal('0.01'))}** за унцию.\n\n"
            f"Теперь выберите дисконт/премию для покупателя:",
            reply_markup=get_buyer_discount_keyboard(), parse_mode="Markdown"
        )
        await state.set_state(Calculation.buyer_discount_choice)
    except (InvalidOperation, ValueError):
        await message.answer("❌ Ошибка. Пожалуйста, введите вес в виде числа (например, 12.5).")

@router.callback_query(Calculation.buyer_discount_choice, F.data.startswith("set_buyer_discount_"))
async def set_buyer_discount(callback: types.CallbackQuery, state: FSMContext):
    discount = callback.data.split('_')[-1]
    await state.update_data(buyer_discount_choice=discount)
    data = await state.get_data()
    if data.get('mode') == 'resale':
        prompt = "Введите комиссию 'Продажа USDT' в % (например, `0.6`):"
        await state.set_state(Calculation.commission_usdt)
    else:
        await state.update_data(commission_usdt='0')
        prompt = "Введите комиссию 'Доставка' в % (например, `0` или `-0.4`):"
        await state.set_state(Calculation.commission_delivery)
    await callback.message.edit_text(prompt)
    await callback.answer()

async def process_commission_input(message: types.Message, state: FSMContext, current_field: str, next_state: Calculation, prompt: str):
    try:
        value = message.text.replace(',', '.').strip()
        Decimal(value)
        await state.update_data({current_field: value})
        await message.answer(prompt)
        await state.set_state(next_state)
    except (InvalidOperation, ValueError):
        await message.answer("❌ Ошибка. Пожалуйста, введите комиссию в виде числа.")

@router.message(Calculation.commission_usdt)
async def process_usdt(message: types.Message, state: FSMContext):
    await process_commission_input(message, state, 'commission_usdt', Calculation.commission_delivery, "Введите комиссию 'Доставка' в %:")
@router.message(Calculation.commission_delivery)
async def process_delivery(message: types.Message, state: FSMContext):
    await process_commission_input(message, state, 'commission_delivery', Calculation.commission_courier, "Введите комиссию 'Курьер' в %:")
@router.message(Calculation.commission_courier)
async def process_courier(message: types.Message, state: FSMContext):
    await process_commission_input(message, state, 'commission_courier', Calculation.commission_agent, "Введите комиссию 'Агента' в %:")
@router.message(Calculation.commission_agent)
async def process_agent(message: types.Message, state: FSMContext):
    await process_commission_input(message, state, 'commission_agent', Calculation.commission_partner, "Введите комиссию 'Партнера' в %:")

@router.message(Calculation.commission_partner)
async def process_partner(message: types.Message, state: FSMContext):
    try:
        value = message.text.replace(',', '.').strip()
        Decimal(value)
        await state.update_data(commission_partner=value)
        user_data = await state.get_data()
        usdt_commission_line = f"\n- **Комиссия USDT:** {user_data.get('commission_usdt', 'N/A')}%" if user_data.get('mode') == 'resale' else ''
        confirmation_text = f"""
Пожалуйста, проверьте введенные данные:
- **Режим:** {user_data['mode']}
- **Вес партии:** {user_data['weight']} кг
- **Дисконт покупателя:** {user_data['buyer_discount_choice']}% от цены MOEX{usdt_commission_line}
- **Комиссия Доставка:** {user_data['commission_delivery']}%
- **Комиссия Курьер:** {user_data['commission_courier']}%
- **Комиссия Агента:** {user_data['commission_agent']}%
- **Комиссия Партнера:** {user_data['commission_partner']}%
Нажмите 'Рассчитать' для получения результата.
"""
        await message.answer(confirmation_text, reply_markup=get_confirmation_keyboard(), parse_mode="Markdown")
        await state.set_state(Calculation.confirm)
    except (InvalidOperation, ValueError):
        await message.answer("❌ Ошибка. Пожалуйста, введите число.")

@router.callback_query(Calculation.confirm, F.data == "confirm_calculation")
async def confirm_and_calculate(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⏳ Финальный расчет...")
    user_data = await state.get_data()
    cbr_rate = await get_cbr_usd_rate()
    if not cbr_rate:
        await callback.message.answer("❌ Не удалось получить курс с ЦБ. Попробуйте позже.")
        await state.clear(); return
    params_to_calc = { **user_data, "cbr_rate": cbr_rate }
    results = calculate_final_deal(params_to_calc)
    if not results:
        await callback.message.answer("❌ Произошла внутренняя ошибка при расчете."); await state.clear(); return
    res = results
    text = f"""
✅ **Результаты расчета ({user_data['mode']})**
**Итоговая цена для клиента:**
- `Цена за грамм: {res['client_price_gram_rub']} RUB`
- `Цена за всю партию ({res['weight_kg']} кг): {res['total_client_price_rub']} RUB`
**Ваша чистая прибыль:**
- `За всю партию: {res['total_profit_rub']} RUB / {res['total_profit_usd']} USD`
- `Процент прибыли: {res['profit_percent']}%`
---
*Исходные данные:*
- *Базовая цена унции (MOEX): ${res['base_supplier_price_usd_ounce'].quantize(Decimal('0.01'))}*
- *Цена унции для покупателя: ${res['buyer_price_usd_ounce'].quantize(Decimal('0.01'))}*
- *Курс ЦБ РФ: {res['cbr_rate']}*
- *Курс MOEX: {user_data['moex_usd_rate']}*
"""
    log_id = await db.log_calculation(callback.from_user.id, results, params_to_calc)
    await callback.message.edit_text(text, reply_markup=get_report_keyboard(str(log_id)), parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data.startswith("send_report_"))
async def send_report_to_chat(callback: types.CallbackQuery):
    log_id = callback.data.split("_")[-1]
    log_entry = await db.get_log_by_id(log_id)
    if not log_entry:
        await callback.answer("Не удалось найти запись для отчета.", show_alert=True)
        return
    p = log_entry['parameters']
    r = log_entry['result']
    usdt_line = f"Комиссия USDT: {p.get('commission_usdt', 'N/A')}%\n" if p.get('mode') == 'resale' else ''
    timestamp_utc = log_entry['timestamp']
    report_text = f"""
**📈 Фиксация сделки**
**Режим:** {p['mode']}
**Источник:** MOEX
**Вес партии:** {p['weight']} кг
---
**ПАРАМЕТРЫ СДЕЛКИ:**
- Цена покупателя (расч.): ${r['buyer_price_usd_ounce']} / унция
- Дисконт от базовой цены: {p['buyer_discount_choice']}%
{usdt_line}- Доставка: {p['commission_delivery']}%
- Курьер: {p['commission_courier']}%
- Агент: {p['commission_agent']}%
- Партнер: {p['commission_partner']}%
---
**КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ:**
- **Цена для клиента (за грамм):** `{r['client_price_gram_rub']}` RUB
- **Цена для клиента (за партию):** `{r['total_client_price_rub']}` RUB
- **Чистая прибыль (за партию):** `{r['total_profit_rub']}` RUB / `{r['total_profit_usd']}` USD
- **Маржинальность:** `{r['profit_percent']}`%
---
*Расчет произведен: {timestamp_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC*
*Пользователь: {callback.from_user.full_name} (@{callback.from_user.username})*
"""
    try:
        await callback.bot.send_message(settings.REPORT_CHAT_ID, report_text, parse_mode="Markdown")
        await callback.answer("✅ Отчет успешно отправлен в чат!", show_alert=True)
    except Exception as e:
        logging.error(f"Failed to send report to chat {settings.REPORT_CHAT_ID}: {e}")
        await callback.answer("❌ Ошибка при отправке отчета.", show_alert=True)