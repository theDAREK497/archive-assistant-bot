import os
import asyncio
import aiohttp
import pathlib
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from src.embeddings.indexer import search

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Настройки
EMBED_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LMSTUDIO_MODEL")

# Приветственное сообщение
WELCOME_MESSAGE = """
👋 Привет! Я бот-ассистент компании EORA. 

Я могу ответить на вопросы о наших проектах и решениях на основе нашей базы знаний.

🔍 Просто задайте вопрос, например:
• Что вы можете сделать для ритейлеров?
• Какие проекты вы делали для Dodo Pizza?
• Какие у вас решения для голосовых ассистентов?

Я постараюсь дать подробный ответ со ссылками на наши кейсы!
"""

async def ask_lmstudio(question: str, context: str, sources: list) -> str:
    """Асинхронный запрос к LLM с встроенными ссылками"""
    url = f"{EMBED_URL}/chat/completions"
    
    # Форматируем контекст
    formatted_context = "\n---\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(context.split("\n---\n"))])
    
    # Формируем список источников
    sources_list = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(sources)])
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "Ты — ассистент компании EORA, отвечающий строго по предоставленным данным. "
                    "Отвечай только на основе контекста ниже. Если ответа нет в контексте, скажи 'Не знаю'.\n\n"
                    "### Инструкции:\n"
                    "1. Всегда используй прямой формат ссылок: [описание проекта](полный_URL)\n"
                    "2. Для каждого упоминания проекта добавляй ссылку на соответствующий кейс\n"
                    "3. Пример правильного ответа:\n"
                    "   Для ритейлеров мы предлагаем чат-боты для HR, например [бот для приглашения на собеседования в Магнит](https://eora.ru/cases/chat-boty/hr-bot-dlya-magnit), а также системы компьютерного зрения, например [поиск товаров по фото для KazanExpress](https://eora.ru/cases/kazanexpress-poisk-tovarov-po-foto)\n\n"
                    f"### Источники:\n{sources_list}\n\n"
                    f"### Контекст:\n{formatted_context}"
                )
            },
            {
                "role": "user", 
                "content": f"Вопрос: {question}"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async with session.post(url, json=payload) as response:
            try:
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"]
            except aiohttp.ClientResponseError as e:
                print(f"Chat API error: {e.status} {e.message}")
                return "Ошибка при обработке запроса"
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                return "Произошла непредвиденная ошибка"

@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer(WELCOME_MESSAGE, parse_mode="Markdown")

@dp.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(WELCOME_MESSAGE, parse_mode="Markdown")

@dp.message()
async def handle_message(message: Message):
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите текст вопроса")
        return
        
    processing_msg = await message.answer("🔍 Ищу информацию в базе знаний EORA...")
    
    try:
        chunks = await asyncio.to_thread(search, query, int(os.getenv("TOP_K", 4)))
        if not chunks:
            await processing_msg.edit_text("❌ По вашему запросу ничего не найдено")
            return
            
        context_text = "\n---\n".join([c["text"] for c in chunks])
        
        # Извлекаем URL с проверкой
        sources = []
        for c in chunks:
            url = c.get("url", "")
            if url and url != "unknown_url" and url not in sources:
                sources.append(url)
        
        await processing_msg.edit_text("🤖 Формирую ответ на основе найденных материалов...")
        answer = await ask_lmstudio(query, context_text, sources)
        
        # Отправка ответа
        await processing_msg.edit_text(
            f"💡 **Ответ на ваш вопрос:**\n\n{answer}", 
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Error handling message: {str(e)}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса")

async def main():
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Начать работу с ботом"),
        types.BotCommand(command="help", description="Помощь по использованию бота")
    ])
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Starting EORA Knowledge Assistant...")
    asyncio.run(main())