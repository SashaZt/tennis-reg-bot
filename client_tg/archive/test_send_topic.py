# test_send_topic.py - тест отправки в конкретный топик
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import BOT_TOKEN

async def test_send_to_topic():
    """Тестируем отправку сообщений в топики"""
    bot = Bot(token=BOT_TOKEN)
    
    group_id = -1002635671990
    
    # ID топиков для тестирования (нужно будет получить из первого скрипта)
    test_topic_ids = [
        None,  # Основной чат (без топика)
        # Добавьте сюда ID топиков которые найдем в первом скрипте
        # Например: 123, 456, 789
    ]
    
    try:
        print(f"🧪 Тестируем отправку в различные топики группы {group_id}")
        
        for i, topic_id in enumerate(test_topic_ids):
            try:
                print(f"\n📌 Тест {i+1}: {'Основной чат' if topic_id is None else f'Топик ID {topic_id}'}")
                
                # Создаем тестовое сообщение
                test_text = f"""🧪 **Тестовое сообщение**

📅 Дата: 15.07.2025  
🕐 Время: 19:00
📍 Место: Тестовое место
👥 Мест: ⬜️⬜️⬜️⬜️ (0/4)

📋 Топик: {'Основной' if topic_id is None else topic_id}

*Это тестовое сообщение будет удалено через 10 секунд*"""

                # Создаем кнопки
                builder = InlineKeyboardBuilder()
                builder.add(
                    InlineKeyboardButton(text="✅ Записаться", callback_data=f"test_register_{i}"),
                    InlineKeyboardButton(text="❌ Отменить", callback_data=f"test_cancel_{i}")
                )
                builder.adjust(2)
                
                # Отправляем сообщение
                if topic_id is None:
                    # В основной чат
                    message = await bot.send_message(
                        chat_id=group_id,
                        text=test_text,
                        reply_markup=builder.as_markup(),
                        parse_mode="Markdown"
                    )
                else:
                    # В конкретный топик
                    message = await bot.send_message(
                        chat_id=group_id,
                        text=test_text,
                        message_thread_id=topic_id,
                        reply_markup=builder.as_markup(),
                        parse_mode="Markdown"
                    )
                
                print(f"✅ Сообщение отправлено! ID: {message.message_id}")
                print(f"🧵 Thread ID в ответе: {getattr(message, 'message_thread_id', 'Нет')}")
                
                # Ждем и удаляем
                await asyncio.sleep(10)
                await bot.delete_message(group_id, message.message_id)
                print(f"🗑 Сообщение удалено")
                
            except Exception as e:
                print(f"❌ Ошибка при отправке в {'основной чат' if topic_id is None else f'топик {topic_id}'}: {e}")
        
        # Дополнительный тест - попробуем найти топики через API
        print(f"\n🔍 Дополнительные тесты API...")
        
        # Тест с разными потенциальными ID топиков
        potential_topic_ids = [1, 2, 3, 5, 10, 39]  # 39 из вашей ссылки
        
        for topic_id in potential_topic_ids:
            try:
                print(f"🧪 Пробуем топик ID: {topic_id}")
                test_msg = await bot.send_message(
                    chat_id=group_id,
                    text=f"Тест топика {topic_id} - удалится через 5 сек",
                    message_thread_id=topic_id
                )
                print(f"✅ Успех! Топик {topic_id} существует. Message ID: {test_msg.message_id}")
                
                await asyncio.sleep(5)
                await bot.delete_message(group_id, test_msg.message_id)
                
            except Exception as e:
                print(f"❌ Топик {topic_id} недоступен: {e}")
                
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Тестируем отправку в топики...")
    asyncio.run(test_send_to_topic())