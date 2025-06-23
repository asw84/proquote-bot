from aiogram.fsm.state import State, StatesGroup

class Calculation(StatesGroup):
    mode = State()
    source = State()
    weight = State()
    buyer_discount_choice = State()
    commission_usdt = State()
    commission_delivery = State()
    commission_courier = State()
    commission_agent = State()
    commission_partner = State()
    confirm = State()