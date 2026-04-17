# handlers/user.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.admin import AdminKeyboards
from services.user_service import UserService

from config import config

router = Router()


@router.message(Command("start"))
async def start_command(message: Message):
    """Команда /start - автозапуск админ панели для админов"""

    # Игнорируем команды в группах
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    user_id = message.from_user.id

    # Если пользователь админ - сразу запускаем админ панель
    if user_id in config.admin_ids:

        # Создаем или обновляем админа в БД
        await UserService.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            is_admin=True,
        )

        text = f"""🔧 Панель администратора

Добро пожаловать, {message.from_user.first_name}!

📋 Как это работает:
• Вы создаете события здесь в личном чате
• Бот автоматически публикует их в соответствующие топики группы
• Пользователи записываются через кнопки в группе

Доступные действия:"""

        keyboard = AdminKeyboards.main_menu()
        await message.answer(text, reply_markup=keyboard)
        return

    # Обычный пользователь
    welcome_text = f"""Привет, {message.from_user.first_name}! 👋

🎾 MTA Tennis Academy - Система записи

📍 Как записаться на тренировку:
1️⃣ Перейдите в основную группу
2️⃣ Найдите нужную тренировку в соответствующем топике
3️⃣ Нажмите кнопку "✅ Записаться"
4️⃣ Для отмены нажмите "❌ Отменить запись"

💡 Важно помнить:
• Максимум 4 места на тренировку
• Отмена возможна за 48 часов до события
• Стоимость: 90 злотых

📱 Все действия происходят в группе через кнопки!"""

    await message.answer(welcome_text)


@router.message(Command("help"))
async def help_command(message: Message):
    """Команда /help - только информация"""

    # Игнорируем команды в группах
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    help_text = """🤖 **Справка по использованию**

🎾 **Для записи на тренировки:**
• Все записи происходят в основной группе
• Найдите нужный день недели в топиках группы
• Используйте кнопки "✅ Записаться" / "❌ Отменить запись"

📋 **Топики по дням недели:**
• Понедельник
• Вторник  
• Среда
• Четверг
• Пятница
• Суббота
• Воскресенье
• Тренировка для детей

⚠️ **Важные условия:**
• Отмена возможна не позднее чем за 48 часов
• При более поздней отмене занятие подлежит оплате
• Максимум 4 участника на тренировку
• Стоимость: 90 злотых

👨‍💼 **Для администраторов:**
• Используйте команду `/admin` для создания событий

📞 **Поддержка:**
Если у вас возникли вопросы, обратитесь к администратору."""

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("admin"))
async def redirect_to_admin(message: Message):
    """Перенаправление к админ команде"""

    # Игнорируем команды в группах
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    user_id = message.from_user.id

    if user_id in config.admin_ids:
        await message.answer(
            "🔧 Используйте команду `/admin` для доступа к панели администратора",
            parse_mode="Markdown",
        )
    else:
        await message.answer("❌ У вас нет прав администратора", parse_mode="Markdown")


# Обработчик для всех остальных сообщений
@router.message()
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений ТОЛЬКО в личных чатах"""

    # Игнорируем сообщения из групп/каналов
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    # Обрабатываем только личные сообщения
    if message.chat.type == "private":
        help_text = """❓ **Неизвестная команда**

🎾 **Доступные команды:**
• `/start` - информация о системе
• `/help` - подробная справка

👨‍💼 **Для администраторов:**
• `/admin` - панель управления событиями

📍 **Для записи на тренировки:**
Перейдите в основную группу и используйте кнопки в сообщениях о тренировках."""

        await message.answer(help_text, parse_mode="Markdown")


# @router.callback_query()
# async def debug_user_callbacks(callback: CallbackQuery):
#     """Debug пользовательских callback'ов"""
#     logger.info(f"👤 USER DEBUG: callback от {callback.from_user.id}")
#     logger.info(f"👤 USER Chat ID: {callback.message.chat.id}")
#     logger.info(f"👤 USER callback.data: '{callback.data}'")#     logger.info(f"👤 USER callback.data: '{callback.data}'")
#     logger.info(f"👤 USER callback.data: '{callback.data}'")#     logger.info(f"👤 USER callback.data: '{callback.data}'")
