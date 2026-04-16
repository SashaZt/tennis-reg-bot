# test_group.py - скрипт для тестирования доступа к группе
import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def test_group_access():
    """Тестируем доступ к группе"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"🤖 Бот: {me.first_name} (@{me.username})")
        print(f"📱 ID бота: {me.id}")
        
        # Пробуем разные варианты доступа к группе
        group_identifiers = [
            "MTA_tennis_academy",  # username если группа публичная
            "@MTA_tennis_academy", # с @ если есть
            # Добавьте сюда chat_id если знаете
        ]
        
        for group_id in group_identifiers:
            try:
                print(f"\n🔍 Проверяем доступ к: {group_id}")
                
                # Получаем информацию о чате
                chat = await bot.get_chat(group_id)
                print(f"✅ Найден чат: {chat.title}")
                print(f"📋 Тип: {chat.type}")
                print(f"🆔 Chat ID: {chat.id}")
                print(f"👥 Участников: {chat.member_count if hasattr(chat, 'member_count') else 'Неизвестно'}")
                
                # Проверяем права бота в группе
                bot_member = await bot.get_chat_member(group_id, me.id)
                print(f"🔑 Статус бота: {bot_member.status}")
                
                if hasattr(bot_member, 'can_post_messages'):
                    print(f"📝 Может отправлять сообщения: {bot_member.can_post_messages}")
                if hasattr(bot_member, 'can_edit_messages'):
                    print(f"✏️ Может редактировать сообщения: {bot_member.can_edit_messages}")
                if hasattr(bot_member, 'can_delete_messages'):
                    print(f"🗑 Может удалять сообщения: {bot_member.can_delete_messages}")
                
                # Пробуем получить последние сообщения (если есть права)
                try:
                    # Тестовое сообщение
                    test_message = await bot.send_message(
                        group_id, 
                        "🧪 Тест доступа к группе - сообщение будет удалено через 5 секунд"
                    )
                    print(f"✅ Сообщение отправлено! ID: {test_message.message_id}")
                    
                    # Ждем и удаляем тестовое сообщение
                    await asyncio.sleep(5)
                    await bot.delete_message(group_id, test_message.message_id)
                    print("🗑 Тестовое сообщение удалено")
                    
                except Exception as e:
                    print(f"❌ Не удалось отправить сообщение: {e}")
                
                break  # Если нашли рабочий идентификатор, прекращаем поиск
                
            except Exception as e:
                print(f"❌ Ошибка доступа к {group_id}: {e}")
        
        # Получаем список чатов бота (если есть доступ)
        try:
            print(f"\n📊 Дополнительная информация:")
            updates = await bot.get_updates(limit=10)
            if updates:
                print(f"📨 Последние {len(updates)} обновлений получены")
                for update in updates[-3:]:  # Показываем последние 3
                    if update.message:
                        chat = update.message.chat
                        print(f"💬 Чат: {chat.title or chat.first_name} (ID: {chat.id}, тип: {chat.type})")
            else:
                print("📭 Нет последних обновлений")
        except Exception as e:
            print(f"❌ Не удалось получить обновления: {e}")
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Тестируем доступ бота к группе...")
    asyncio.run(test_group_access())