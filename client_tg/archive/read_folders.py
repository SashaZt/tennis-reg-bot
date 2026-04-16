# read_folders.py - читаем папки/разделы в группе
import asyncio
import json
from aiogram import Bot
from aiogram.types import Message
from config import BOT_TOKEN

async def read_group_folders():
    """Читаем все папки/разделы в группе"""
    bot = Bot(token=BOT_TOKEN)
    
    group_id = -1002635671990
    
    try:
        print(f"📂 Анализируем папки/разделы группы: {group_id}")
        
        # Метод 1: Получаем детальную информацию о чате
        try:
            print("\n🔍 Метод 1: Детальная информация о чате...")
            
            chat = await bot.get_chat(group_id)
            
            # Выводим все доступные поля
            chat_dict = {
                'id': chat.id,
                'type': chat.type,
                'title': chat.title,
                'username': getattr(chat, 'username', None),
                'description': getattr(chat, 'description', None),
                'is_forum': getattr(chat, 'is_forum', None),
                'active_usernames': getattr(chat, 'active_usernames', None),
                'available_reactions': getattr(chat, 'available_reactions', None),
            }
            
            print("📋 Основная информация о чате:")
            for key, value in chat_dict.items():
                if value is not None:
                    print(f"   {key}: {value}")
            
            # Проверяем дополнительные поля которые могут содержать информацию о папках
            additional_fields = [
                'folder_id', 'chat_folder', 'folders', 'categories', 
                'pinned_message', 'slow_mode_delay', 'sticker_set_name',
                'can_set_sticker_set', 'linked_chat_id', 'location'
            ]
            
            print("\n📁 Поиск информации о папках:")
            for field in additional_fields:
                if hasattr(chat, field):
                    value = getattr(chat, field)
                    if value is not None:
                        print(f"   ✅ {field}: {value}")
                    else:
                        print(f"   ⚪ {field}: None")
                else:
                    print(f"   ❌ {field}: не существует")
            
        except Exception as e:
            print(f"❌ Метод 1 не сработал: {e}")
        
        # Метод 2: Анализируем структуру сообщений
        try:
            print(f"\n🔍 Метод 2: Анализ структуры сообщений...")
            
            # Получаем последние сообщения
            updates = await bot.get_updates(limit=100)
            
            group_messages = []
            for update in updates:
                if (update.message and 
                    update.message.chat.id == group_id):
                    group_messages.append(update.message)
            
            print(f"📨 Найдено сообщений из группы: {len(group_messages)}")
            
            # Анализируем поля сообщений которые могут указывать на папки
            message_fields = set()
            special_messages = []
            
            for msg in group_messages:
                # Собираем все поля сообщения
                for attr in dir(msg):
                    if not attr.startswith('_'):
                        message_fields.add(attr)
                
                # Ищем специальные типы сообщений
                if hasattr(msg, 'content_type'):
                    if msg.content_type != 'text':
                        special_messages.append({
                            'type': msg.content_type,
                            'date': msg.date,
                            'from': msg.from_user.first_name if msg.from_user else 'Unknown'
                        })
                
                # Проверяем специфичные поля
                special_fields = [
                    'reply_markup', 'message_thread_id', 'reply_to_message',
                    'forward_from', 'forward_from_chat', 'edit_date',
                    'media_group_id', 'author_signature'
                ]
                
                for field in special_fields:
                    if hasattr(msg, field):
                        value = getattr(msg, field)
                        if value is not None:
                            print(f"   📌 Сообщение с {field}: {value}")
            
            print(f"\n📊 Уникальные поля сообщений: {len(message_fields)}")
            print(f"🎯 Специальных сообщений: {len(special_messages)}")
            
            if special_messages:
                print("📋 Типы специальных сообщений:")
                for msg in special_messages[-5:]:  # Последние 5
                    print(f"   {msg['type']} от {msg['from']} в {msg['date']}")
            
        except Exception as e:
            print(f"❌ Метод 2 не сработал: {e}")
        
        # Метод 3: Попытка получить админские данные
        try:
            print(f"\n🔍 Метод 3: Админская информация...")
            
            # Получаем список администраторов
            admins = await bot.get_chat_administrators(group_id)
            print(f"👑 Администраторов: {len(admins)}")
            
            for admin in admins:
                print(f"   👤 {admin.user.first_name} ({admin.status})")
                
                # Проверяем права администратора
                admin_rights = []
                rights_fields = [
                    'can_manage_chat', 'can_delete_messages', 'can_manage_video_chats',
                    'can_restrict_members', 'can_promote_members', 'can_change_info',
                    'can_invite_users', 'can_post_messages', 'can_edit_messages',
                    'can_pin_messages', 'can_manage_topics'
                ]
                
                for right in rights_fields:
                    if hasattr(admin, right):
                        value = getattr(admin, right)
                        if value:
                            admin_rights.append(right)
                
                if admin_rights and admin.user.id == (await bot.get_me()).id:
                    print(f"   🤖 Права бота: {', '.join(admin_rights)}")
            
        except Exception as e:
            print(f"❌ Метод 3 не сработал: {e}")
        
        # Метод 4: Попытка чтения через сырые данные
        try:
            print(f"\n🔍 Метод 4: Сырые данные чата...")
            
            # Получаем сырую информацию если возможно
            chat_raw = await bot.get_chat(group_id)
            
            # Пробуем получить JSON представление
            if hasattr(chat_raw, 'model_dump'):
                raw_data = chat_raw.model_dump()
                print("📄 Сырые данные чата:")
                print(json.dumps(raw_data, indent=2, default=str, ensure_ascii=False)[:1000] + "...")
            
        except Exception as e:
            print(f"❌ Метод 4 не сработал: {e}")
        
        # Метод 5: Тестирование различных API методов
        try:
            print(f"\n🔍 Метод 5: Тестирование API методов...")
            
            api_methods = [
                'get_chat_menu_button',
                'get_my_commands', 
                'get_chat_member_count'
            ]
            
            for method_name in api_methods:
                try:
                    if hasattr(bot, method_name):
                        method = getattr(bot, method_name)
                        if method_name == 'get_chat_member_count':
                            result = await method(group_id)
                        else:
                            result = await method()
                        print(f"   ✅ {method_name}: {result}")
                    else:
                        print(f"   ❌ {method_name}: метод не существует")
                except Exception as e:
                    print(f"   ⚪ {method_name}: {e}")
            
        except Exception as e:
            print(f"❌ Метод 5 не сработал: {e}")
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Читаем папки/разделы группы...")
    asyncio.run(read_group_folders())