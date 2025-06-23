from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from decimal import Decimal

def get_mode_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Перепродажа", callback_data="set_mode_resale"))
    builder.row(InlineKeyboardButton(text="Под сделку", callback_data="set_mode_deal"))
    return builder.as_markup()

def get_source_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Источники: MOEX", callback_data="set_source_moex"))
    builder.row(InlineKeyboardButton(text="Источники: ProFinance", callback_data="set_source_profinance"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_calculation"))
    return builder.as_markup()

def get_buyer_discount_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = []
    for i in range(-10, 11, 1):
        val = Decimal(i) / 10
        buttons.append(InlineKeyboardButton(text=f"{val:+.1f}%", callback_data=f"set_buyer_discount_{val}"))
    for i in range(0, len(buttons), 5):
        builder.row(*buttons[i:i+5])
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_calculation"))
    return builder.as_markup()

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Рассчитать", callback_data="confirm_calculation"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_calculation"))
    return builder.as_markup()

def get_report_keyboard(log_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📌 Зафиксировать и отправить в чат", callback_data=f"send_report_{log_id}"))
    return builder.as_markup()