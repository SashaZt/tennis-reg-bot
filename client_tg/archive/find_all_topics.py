# find_all_topics_fixed.py - ищем все топики включая детские
import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def find_all_topics():
    """Ищем все топики включая детские тренировки"""
    bot = Bot(token=BOT_TOKEN)
    
    group_id = -1002635671990
    
    try:
        print(f"🔍 Ищем ВСЕ топики в группе: {group_id}")
        
        # Метод 1: Последовательный поиск всех существующих топиков
        print(f"\n🔢 Метод 1: Поиск всех топиков 1-200...")
        
        all_existing = []
        
        for topic_id in range(1, 201):  # Расширили до 200
            try:
                test_msg = await bot.send_message(
                    chat_id=group_id,
                    text=f"🔍 Тест топика {topic_id}",
                    message_thread_id=topic_id
                )
                
                print(f"✅ Топик ID {topic_id} существует")
                all_existing.append(topic_id)
                
                await bot.delete_message(group_id, test_msg.message_id)
                await asyncio.sleep(0.3)  # Небольшая пауза
                
            except Exception as e:
                if "thread not found" not in str(e).lower():
                    if topic_id <= 50:  # Показываем ошибки только для первых 50
                        print(f"⚠️ ID {topic_id}: {e}")
                
                # Паузы для избежания лимитов
                if topic_id % 20 == 0:
                    await asyncio.sleep(2)
                    print(f"   📊 Проверено {topic_id}/200 топиков...")
        
        print(f"\n📊 Найдено существующих топиков: {all_existing}")
        
        # Метод 2: Анализ ForumTopicCreated событий из истории
        print(f"\n📨 Метод 2: Анализ истории создания топиков...")
        
        all_topic_creates = []
        
        try:
            # Получаем максимум обновлений
            updates = await bot.get_updates(limit=1000)
            
            for update in updates:
                if (update.message and 
                    update.message.chat.id == group_id and
                    hasattr(update.message, 'forum_topic_created') and
                    update.message.forum_topic_created):
                    
                    topic_info = update.message.forum_topic_created
                    all_topic_creates.append({
                        'name': topic_info.name,
                        'message_thread_id': update.message.message_thread_id,
                        'icon_color': topic_info.icon_color,
                        'emoji_id': topic_info.icon_custom_emoji_id,
                        'date': update.message.date
                    })
            
            print(f"🎯 Найдено событий создания топиков: {len(all_topic_creates)}")
            
            for topic in all_topic_creates:
                print(f"   📌 '{topic['name']}' - ID: {topic['message_thread_id']}")
                print(f"      Дата: {topic['date']}")
                if topic['emoji_id']:
                    print(f"      Эмодзи ID: {topic['emoji_id']}")
                print()
                
        except Exception as e:
            print(f"❌ Ошибка при поиске истории топиков: {e}")
        
        # Метод 3: Поиск сообщений с упоминанием "детей"
        print(f"\n👶 Метод 3: Поиск сообщений о детских тренировках...")
        
        kids_keywords = ["детей", "ребенок", "дети", "child", "kid", "junior", "детская", "детский"]
        kids_messages = []
        
        try:
            updates = await bot.get_updates(limit=1000)
            
            for update in updates:
                if (update.message and 
                    update.message.chat.id == group_id and
                    update.message.text):
                    
                    text_lower = update.message.text.lower()
                    
                    for keyword in kids_keywords:
                        if keyword in text_lower:
                            kids_messages.append({
                                'text': update.message.text[:200],
                                'thread_id': getattr(update.message, 'message_thread_id', None),
                                'date': update.message.date,
                                'from': update.message.from_user.first_name if update.message.from_user else 'Unknown'
                            })
                            break
            
            print(f"👶 Найдено сообщений о детях: {len(kids_messages)}")
            
            kids_topics = set()
            for msg in kids_messages[-10:]:  # Последние 10
                print(f"   📝 '{msg['text'][:100]}...'")
                print(f"      Топик ID: {msg['thread_id']}")
                print(f"      От: {msg['from']} в {msg['date']}")
                print()
                
                if msg['thread_id']:
                    kids_topics.add(msg['thread_id'])
            
            print(f"👶 Уникальные топики с упоминанием детей: {list(kids_topics)}")
                
        except Exception as e:
            print(f"❌ Ошибка при поиске детских сообщений: {e}")
        
        # Метод 4: Проверка конкретных "детских" ID
        print(f"\n🎯 Метод 4: Проверка потенциальных детских топиков...")
        
        # Потенциальные ID для детских тренировок
        potential_kids_ids = [
            100, 101, 102,  # Высокие числа
            50, 51, 52,     # Средние числа  
            8, 9, 10,       # После дней недели (1-7)
            99, 98, 97,     # Обратный отсчет от 100
        ]
        
        kids_topics_found = []
        
        for topic_id in potential_kids_ids:
            try:
                test_msg = await bot.send_message(
                    chat_id=group_id,
                    text=f"🧒 Тест детского топика {topic_id}",
                    message_thread_id=topic_id
                )
                
                print(f"✅ Потенциальный детский топик ID {topic_id} существует!")
                kids_topics_found.append(topic_id)
                
                await bot.delete_message(group_id, test_msg.message_id)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                if "thread not found" not in str(e).lower():
                    print(f"⚠️ Детский ID {topic_id}: {e}")
        
        # Финальный отчет
        print(f"\n📋 === ФИНАЛЬНЫЙ ОТЧЕТ ===")
        print(f"📊 Всего найдено топиков: {len(all_existing)}")
        print(f"👶 Потенциальных детских: {len(kids_topics_found)}")
        
        # Создаем полный mapping
        print(f"\n🗂 Все найденные топики:")
        
        # Известные топики из анализа
        known_names = {}
        for topic in all_topic_creates:
            known_names[topic['message_thread_id']] = topic['name']
        
        for topic_id in sorted(all_existing):
            name = known_names.get(topic_id, "❓ Неизвестный")
            kids_mark = "👶" if topic_id in kids_topics_found else ""
            print(f"   {topic_id}: {name} {kids_mark}")
        
        # Рекомендуемая конфигурация
        print(f"\n⚙️ Рекомендуемая конфигурация для config.py:")
        print(f"# Топики по дням недели")
        print(f"WEEKDAY_TOPICS = {{")
        
        # Предлагаем mapping основываясь на названиях
        weekday_mapping = {}
        
        for topic in all_topic_creates:
            name_lower = topic['name'].lower()
            topic_id = topic['message_thread_id']
            
            if 'понедельник' in name_lower or 'monday' in name_lower:
                weekday_mapping[0] = topic_id
            elif 'вторник' in name_lower or 'tuesday' in name_lower:
                weekday_mapping[1] = topic_id
            elif 'среда' in name_lower or 'wednesday' in name_lower:
                weekday_mapping[2] = topic_id
            elif 'четверг' in name_lower or 'thursday' in name_lower:
                weekday_mapping[3] = topic_id
            elif 'пятница' in name_lower or 'friday' in name_lower:
                weekday_mapping[4] = topic_id
            elif 'суббота' in name_lower or 'saturday' in name_lower:
                weekday_mapping[5] = topic_id
            elif 'воскресенье' in name_lower or 'sunday' in name_lower:
                weekday_mapping[6] = topic_id
        
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        
        for i, day in enumerate(weekdays):
            topic_id = weekday_mapping.get(i, "❓")
            print(f"    {i}: {topic_id},  # {day}")
        
        print(f"}}")
        
        # Детские топики
        if kids_topics_found:
            print(f"\n# Детские тренировки") 
            print(f"KIDS_TOPICS = {kids_topics_found}")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Ищем ВСЕ топики включая детские...")
    asyncio.run(find_all_topics())