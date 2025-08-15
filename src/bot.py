import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from src.embeddings.indexer import search
from src.rag.prompt_builder import build_system_prompt
from src.rag.response_formatter import add_html_links

# Инициализация бота
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Настройки
CHAT_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LMSTUDIO_MODEL", "TheBloke/Saiga2-7B-GGUF")
TOP_K = int(os.getenv("TOP_K", 2))
REQUEST_TIMEOUT = 120

# Сообщения
WELCOME_MESSAGE = """
👋 Здравствуйте! Я умный помощник компании EORA — ваш проводник в мире наших разработок и решений.

С моей помощью вы можете:
• Узнать о наших проектах и технологиях
• Получить примеры решений для вашей отрасли
• Найти кейсы по конкретным задачам

Просто задайте вопрос, например:
• Что вы можете предложить для ритейлеров?
• Какие решения у вас есть для банков?
• Покажите кейсы по голосовым ассистентам

Я найду самую релевантную информацию в нашей базе знаний и даду развернутый ответ со ссылками на источники.
"""

HELP_MESSAGE = """
🛠️ Как работать с ботом:

1. Задайте вопрос о решениях EORA
2. Я поищу информацию в нашей базе знаний
3. Сформирую ответ на основе найденных материалов
4. В ответе будут указаны источники в формате чисел - это кликабельные ссылки

Примеры вопросов:
• Какие решения вы предлагаете для e-commerce?
• Что вы делали для Dodo Pizza?
• Какие проекты у вас есть в сфере AI?

⏱️ Генерация ответа может занять до 1 минуты. Пожалуйста, наберитесь терпения!

Если что-то пошло не так, используйте команду /start для перезапуска.
"""

async def ask_lmstudio(question: str, context: str, sources: list) -> str:
    """
    Асинхронный запрос к LLM для генерации ответа
    Возвращает сгенерированный текст или сообщение об ошибке
    """
    url = f"{CHAT_URL}/chat/completions"
    
    # Формируем системный промпт
    system_prompt = build_system_prompt(context, sources)
    
    # Формируем запрос
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
        "stop": ["\n\n"]
    }
    
    # Выполняем запрос с таймаутом
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        except asyncio.TimeoutError:
            return "⚠️ Генерация ответа заняла слишком много времени."
        except aiohttp.ClientError as e:
            print(f"HTTP ошибка: {str(e)}")
            return "⚠️ Ошибка соединения с сервером генерации."
        except Exception as e:
            print(f"Ошибка запроса: {str(e)}")
            return "⚠️ Произошла ошибка при генерации ответа."

@dp.message(Command("start"))
async def handle_start(message: Message):
    """Обработка команды /start - приветственное сообщение"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Помощь")],
            [types.KeyboardButton(text="Примеры вопросов")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(WELCOME_MESSAGE, 
                         parse_mode=None,
                         reply_markup=keyboard)

@dp.message(Command("help"))
async def handle_help(message: Message):
    """Обработка команды /help - инструкции по использованию"""
    await message.answer(HELP_MESSAGE, parse_mode=None)

@dp.message(lambda message: message.text == "Помощь")
async def handle_help_button(message: Message):
    """Обработка кнопки 'Помощь'"""
    await handle_help(message)

@dp.message(lambda message: message.text == "Примеры вопросов")
async def handle_examples(message: Message):
    """Обработка кнопки 'Примеры вопросов'"""
    examples = (
        "Вот примеры вопросов, которые вы можете задать:\n\n"
        "• Что вы можете предложить для банковской сферы?\n"
        "• Покажите кейсы по автоматизации колл-центров\n"
        "• Какие решения у вас есть для ритейла?\n"
        "• Что вы делали для KazanExpress?\n"
        "• Расскажите о проектах в сфере медицины"
    )
    await message.answer(examples, parse_mode=None)

@dp.message()
async def handle_message(message: Message):
    """Обработка пользовательских сообщений"""
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите текст вопроса", parse_mode=None)
        return
        
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("🔍 Ищу информацию в базе знаний EORA...", parse_mode=None)
    
    try:
        # Поиск релевантных чанков
        chunks = await asyncio.to_thread(search, query, TOP_K)
        if not chunks:
            await processing_msg.edit_text("❌ По вашему запросу ничего не найдено", parse_mode=None)
            return
            
        # Формируем контекст из найденных чанков
        context_text = "\n---\n".join([c["text"] for c in chunks])
        
        # Извлекаем уникальные URL источников
        sources = []
        for c in chunks:
            url = c.get("url", "")
            if url and url != "unknown_url" and url not in sources:
                sources.append(url)
        
        # Обновляем статус
        await processing_msg.edit_text("🤖 Формирую ответ на основе найденных материалов...", parse_mode=None)
        
        # Генерация ответа
        answer = await ask_lmstudio(query, context_text, sources)
        
        # Проверка пустого ответа
        if not answer.strip():
            answer = "⚠️ Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."
        
        # Форматируем ответ с HTML-ссылками
        html_answer = add_html_links(answer, sources)
        
        # Отправка финального ответа
        await processing_msg.edit_text(
            html_answer, 
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Ошибка обработки: {str(e)}")
        await message.answer("⚠️ Произошла критическая ошибка при обработке запроса", parse_mode=None)

async def main():
    """Основная функция запуска бота"""
    # Установка команд меню
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Начать работу"),
        types.BotCommand(command="help", description="Помощь по использованию")
    ])
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Запуск EORA Knowledge Assistant...")
    asyncio.run(main())