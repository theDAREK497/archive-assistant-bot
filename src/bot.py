import os
import asyncio
import aiohttp
import re
import pathlib
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from src.embeddings.indexer import search

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Настройки
EMBED_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
CHAT_URL = os.getenv("LMSTUDIO_CHAT_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LMSTUDIO_MODEL", "TheBloke/Saiga2-7B-GGUF")
TOP_K = int(os.getenv("TOP_K", 2))

# Уникальные сообщения
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
4. В ответе будут указаны источники в формате [1], [2] - это кликабельные ссылки

Примеры вопросов:
• Какие решения вы предлагаете для e-commerce?
• Что вы делали для Dodo Pizza?
• Какие проекты у вас есть в сфере AI?

⏱️ Генерация ответа может занять до 1 минуты. Пожалуйста, наберитесь терпения!

Если что-то пошло не так, используйте команду /start для перезапуска.
"""

async def ask_lmstudio(question: str, context: str, sources: list) -> str:
    """Асинхронный запрос к LLM с новым форматом ссылок"""
    url = f"{CHAT_URL}/chat/completions"
    
    # Формируем список источников для промпта
    sources_list = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(sources)])
    
    # Промпт для генерации ответа
    system_prompt = (
        "Ты — ассистент компании EORA. Отвечай строго по контексту ниже. "
        "Используй только факты из контекста.\n\n"
        "### Инструкции:\n"
        "1. Для каждого упоминания проекта ставь номер источника в квадратных скобках: [1], [2] и т.д.\n"
        "2. НЕ создавай отдельный раздел 'Источники' в конце ответа.\n"
        "3. НЕ делай слова кликабельными, только номера в квадратных скобках.\n"
        "4. Ответ давать краткий и содержательный.\n"
        "5. Пример правильного ответа:\n"
        "   Для ритейлеров мы предлагаем чат-боты для HR [1] и системы компьютерного зрения [2].\n\n"
        f"### Источники:\n{sources_list}\n\n"
        f"### Контекст:\n{context[:2000]}"  # Ограничиваем длину контекста
    )
    
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
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=180)) as session:
        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        except asyncio.TimeoutError:
            return "Генерация ответа заняла слишком много времени."
        except Exception as e:
            print(f"Ошибка запроса: {str(e)}")
            return "Произошла ошибка при генерации ответа."

def add_links_to_answer(answer: str, sources: list) -> str:
    """Добавляет markdown-ссылки к номерам [1], [2] в ответе"""
    # Создаем маппинг номеров на URL
    source_map = {str(i+1): url for i, url in enumerate(sources)}
    
    # Регулярка для поиска [1], [2] и т.д.
    pattern = r'\[(\d+)\]'
    
    def replace_match(match):
        num = match.group(1)
        url = source_map.get(num)
        if url:
            return f"[{num}]({url})"
        return match.group(0)
    
    return re.sub(pattern, replace_match, answer)

@dp.message(Command("start"))
async def handle_start(message: Message):
    """Приветственное сообщение с кнопкой помощи"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Помощь")],
            [types.KeyboardButton(text="Примеры вопросов")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(WELCOME_MESSAGE, 
                         parse_mode="Markdown", 
                         reply_markup=keyboard)

@dp.message(Command("help"))
async def handle_help(message: Message):
    """Сообщение с инструкциями"""
    await message.answer(HELP_MESSAGE, parse_mode="Markdown")

@dp.message(lambda message: message.text == "Помощь")
async def handle_help_button(message: Message):
    await handle_help(message)

@dp.message(lambda message: message.text == "Примеры вопросов")
async def handle_examples(message: Message):
    examples = (
        "Вот примеры вопросов, которые вы можете задать:\n\n"
        "• Что вы можете предложить для банковской сферы?\n"
        "• Покажите кейсы по автоматизации колл-центров\n"
        "• Какие решения у вас есть для ритейла?\n"
        "• Что вы делали для KazanExpress?\n"
        "• Расскажите о проектах в сфере медицины"
    )
    await message.answer(examples)

@dp.message()
async def handle_message(message: Message):
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите текст вопроса")
        return
        
    processing_msg = await message.answer("🔍 Ищу информацию в базе знаний EORA...")
    
    try:
        chunks = await asyncio.to_thread(search, query, TOP_K)
        if not chunks:
            await processing_msg.edit_text("❌ По вашему запросу ничего не найдено")
            return
            
        context_text = "\n---\n".join([c["text"] for c in chunks])
        
        # Извлекаем уникальные конечные URL
        sources = []
        for c in chunks:
            url = c.get("url", "")
            if url and url != "unknown_url" and url not in sources:
                sources.append(url)
        
        await processing_msg.edit_text("🤖 Формирую ответ на основе найденных материалов...")
        
        # Генерация ответа
        try:
            answer = await asyncio.wait_for(
                ask_lmstudio(query, context_text, sources), 
                timeout=60.0
            )
        except asyncio.TimeoutError:
            answer = "⚠️ Генерация ответа заняла слишком много времени."
        
        # Добавляем ссылки к номерам [1], [2]
        linked_answer = add_links_to_answer(answer, sources)
        
        # Отправка ответа
        await processing_msg.edit_text(
            f"💡 **Ответ на ваш вопрос:**\n\n{linked_answer}", 
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Ошибка обработки: {str(e)}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса")

async def main():
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Начать работу"),
        types.BotCommand(command="help", description="Помощь по использованию")
    ])
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Запуск EORA Knowledge Assistant...")
    asyncio.run(main())