from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='▶️ Начать новый расчет'),
        BotCommand(command='/cancel', description='❌ Отменить текущий расчет')
    ]
    await bot.set_my_commands(main_menu_commands, BotCommandScopeDefault())