# test_topics.py - скрипт для получения тем/топиков группы
import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def get_group_topics():
    """Получаем темы/топики из группы"""
    bot = Bot(token=BOT_TOKEN)
    
    # ID группы которую мы нашли
    group_id = -1002635671990
    
    try:
        print(f"🔍 Анализируем группу: {group_id}")
        
        # Получаем информацию о чате
        chat = await bot.get_chat(group_id)
        print(f"📋 Группа: {chat.title}")
        print(f"🔧 Тип: {chat.type}")
        
        # Проверяем есть ли форум/топики
        if hasattr(chat, 'is_forum'):
            print(f"🗂 Это форум: {chat.is_forum}")
        else:
            print("🗂 Поле is_forum не найдено")
        
        # Пробуем получить топики через getForumTopicIconStickers
        try:
            print("\n🎯 Пытаемся получить иконки топиков...")
            # Этот метод есть только если группа - форум
            stickers = await bot.get_forum_topic_icon_stickers()
            print(f"✅ Получены иконки топиков: {len(stickers)}")
        except Exception as e:
            print(f"❌ Не удалось получить иконки топиков: {e}")
        
        # Пробуем получить последние сообщения и посмотреть на message_thread_id
        try:
            print("\n📨 Анализируем последние обновления...")
            updates = await bot.get_updates(limit=50)
            
            if updates:
                topics_found = set()
                for update in updates:
                    if update.message and update.message.chat.id == group_id:
                        msg = update.message
                        thread_id = getattr(msg, 'message_thread_id', None)
                        
                        if thread_id:
                            topics_found.add(thread_id)
                            print(f"📌 Найден топик ID: {thread_id}")
                            print(f"   Сообщение: {msg.text[:50] if msg.text else 'Нет текста'}...")
                            print(f"   От: {msg.from_user.first_name if msg.from_user else 'Неизвестно'}")
                            print(f"   Дата: {msg.date}")
                            print()
                
                if topics_found:
                    print(f"🎯 Всего найдено уникальных топиков: {len(topics_found)}")
                    print(f"📋 ID топиков: {list(topics_found)}")
                else:
                    print("❌ Топики не найдены в последних сообщениях")
            else:
                print("📭 Нет обновлений для анализа")
                
        except Exception as e:
            print(f"❌ Ошибка при анализе обновлений: {e}")
        
        # Пробуем отправить тестовое сообщение в основной чат
        try:
            print("\n🧪 Отправляем тестовое сообщение...")
            test_msg = await bot.send_message(
                group_id,
                "🔍 Тест извлечения топиков - сообщение будет удалено"
            )
            print(f"✅ Сообщение отправлено в основной чат. ID: {test_msg.message_id}")
            
            # Проверяем есть ли thread_id в отправленном сообщении
            thread_id = getattr(test_msg, 'message_thread_id', None)
            print(f"🧵 Thread ID отправленного сообщения: {thread_id}")
            
            await asyncio.sleep(3)
            await bot.delete_message(group_id, test_msg.message_id)
            print("🗑 Тестовое сообщение удалено")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке тестового сообщения: {e}")
        
        # Пробуем получить информацию о правах администратора
        try:
            print("\n🔑 Проверяем права бота...")
            me = await bot.get_me()
            member = await bot.get_chat_member(group_id, me.id)
            
            print(f"👤 Статус: {member.status}")
            
            # Проверяем специфичные права для форумов
            permissions = [
                'can_manage_topics', 'can_post_messages', 'can_edit_messages',
                'can_delete_messages', 'can_manage_chat'
            ]
            
            for perm in permissions:
                if hasattr(member, perm):
                    value = getattr(member, perm)
                    print(f"🔧 {perm}: {value}")
                    
        except Exception as e:
            print(f"❌ Ошибка при проверке прав: {e}")
        
        # Дополнительная информация о чате
        print(f"\n📊 Дополнительная информация:")
        print(f"🆔 Chat ID: {chat.id}")
        print(f"📱 Username: {getattr(chat, 'username', 'Нет')}")
        print(f"📝 Description: {getattr(chat, 'description', 'Нет')[:100] if getattr(chat, 'description', None) else 'Нет'}")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Анализируем топики группы...")
    asyncio.run(get_group_topics())