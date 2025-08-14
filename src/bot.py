import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from src.embeddings.indexer import search

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Раздельные URL для эмбеддингов и чата
EMBED_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
CHAT_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LMSTUDIO_MODEL")

async def ask_lmstudio(question: str, context: str) -> str:
    """Асинхронный запрос к LLM"""
    url = f"{CHAT_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "Ты — ассистент компании EORA, отвечающий строго по предоставленным данным. "
                    "Отвечай только на основе контекста ниже. Если ответа нет в контексте, скажи 'Не знаю'."
                )
            },
            {
                "role": "user", 
                "content": f"Контекст:\n{context}\n\nВопрос: {question}"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 512
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

@dp.message()
async def handle_message(message: Message):
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите текст вопроса")
        return
        
    # Уведомление о начале обработки
    processing_msg = await message.answer("🔍 Поиск информации...")
    
    try:
        # Асинхронный поиск в FAISS
        chunks = await asyncio.to_thread(search, query, int(os.getenv("TOP_K", 4)))
        context_text = "\n---\n".join([c["text"] for c in chunks])
        
        if not context_text:
            await message.answer("Не найдено информации по вашему запросу")
            return
            
        # Уведомление о генерации ответа
        await processing_msg.edit_text("🤖 Генерация ответа...")
        
        # Асинхронный запрос к LLM
        answer = await ask_lmstudio(query, context_text)
        
        # Отправка ответа (редактируем исходное сообщение)
        await processing_msg.edit_text(answer, parse_mode="Markdown")
    except Exception as e:
        print(f"Error handling message: {str(e)}")
        await message.answer("Произошла ошибка при обработке запроса")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Starting Telegram bot...")
    asyncio.run(main())