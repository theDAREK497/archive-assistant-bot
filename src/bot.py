import asyncio
import os
import re

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
TOP_K = int(os.getenv("TOP_K", "2"))
REQUEST_TIMEOUT = 120  # Таймаут запросов в секундах

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
        except TimeoutError:
            return "⚠️ Генерация ответа заняла слишком много времени."
        except aiohttp.ClientError as e:
            print(f"HTTP ошибка: {e!s}")
            return "⚠️ Ошибка соединения с сервером генерации."
        except Exception as e:
            print(f"Ошибка запроса: {e!s}")
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

async def detect_hallucinations(answer: str, context: str) -> bool:
    """
    Обнаружение возможных галлюцинаций LLM.
    Возвращает True если ответ вероятно содержит галлюцинации.
    """
    answer_lower = answer.lower()
    
    # Очень консервативный подход: только явные признаки галлюцинаций
    uncertainty_phrases = [
        "я не уверен", "не знаю", "не могу сказать", 
        "не имею информации", "не могу найти", "не располагаю данными",
        "у меня нет данных", "информация отсутствует"
    ]
    
    # Если ответ содержит фразы неопределенности - это галлюцинация
    if any(phrase in answer_lower for phrase in uncertainty_phrases):
        return True
    
    # Если ответ содержит ссылки на источники, вероятно это не галлюцинация
    if re.search(r'\[\d+\]', answer):
        return False
        
    # Если ответ очень короткий (менее 5 слов) - не проверяем дальше
    if len(answer.split()) < 5:
        return False
    
    # Очень простой тест на релевантность: проверяем наличие некоторых ключевых слов из контекста
    context_lower = context.lower()
    
    # Извлекаем существительные и прилагательные из контекста (слова длиной > 4 символов)
    context_keywords = set(re.findall(r'\b[а-яё]{5,}\b', context_lower))
    
    # Исключаем самые частые слова
    common_words = {"который", "которые", "которых", "также", "очень", "многие", "другие"}
    context_keywords = context_keywords - common_words
    
    # Берем первые 10 ключевых слов из контекста
    context_sample = list(context_keywords)[:10]
    
    # Если в ответе есть хотя бы одно ключевое слово из контекста, считаем релевантным
    return all(keyword not in answer_lower for keyword in context_sample)
    
    # Если не нашли ни одного совпадения, возможно это галлюцинация
    return True

@dp.message()
async def handle_message(message: Message):
    """Обработка пользовательских сообщений"""
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите текст вопроса", parse_mode=None)
        return
        
    # Общие вопросы, не требующие поиска в базе
    GENERAL_QUESTIONS = {
        "привет": "Здравствуйте! Чем могу помочь?",
        "здравствуй": "Здравствуйте! Задайте вопрос о решениях EORA.",
        "как дела": "У меня всё отлично, я готов отвечать на ваши вопросы о EORA!",
        "помощь": HELP_MESSAGE,
        "что ты умеешь": WELCOME_MESSAGE,
        "спасибо": "Пожалуйста! Обращайтесь ещё!",
    }
    
    query_lower = query.lower()
    if query_lower in GENERAL_QUESTIONS:
        await message.answer(GENERAL_QUESTIONS[query_lower], parse_mode=None)
        return
        
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("🔍 Ищу информацию в базе знаний EORA...", parse_mode=None)
    
    try:
        # Поиск релевантных чанков
        chunks = await asyncio.to_thread(search, query, TOP_K)
        
        # Если ничего не найдено
        if not chunks:
            await processing_msg.edit_text(
                "❌ В нашей базе знаний нет информации по этому вопросу. "
                "Попробуйте задать вопрос о решениях EORA.\n\n"
                "Примеры: /help",
                parse_mode=None
            )
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
        await processing_msg.edit_text("🤖 Формирую ответ...", parse_mode=None)
        
        # Генерация ответа
        answer = await ask_lmstudio(query, context_text, sources)
        
        # Проверка пустого ответа
        if not answer.strip():
            answer = "⚠️ Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."

        # Детекция галлюцинаций (только для нестандартных ответов)
        if not answer.startswith("⚠️") and await detect_hallucinations(answer, context_text):
                answer = (
                    "⚠️ Не удалось найти точную информацию в нашей базе знаний. "
                    "Попробуйте переформулировать вопрос или уточнить детали.\n\n"
                    "Примеры вопросов:\n"
                    "• Какие решения вы предлагаете для e-commerce?\n"
                    "• Что вы делали для Dodo Pizza?\n"
                    "• Какие проекты у вас есть в сфере AI?"
                )
        
        # Проверка релевантности ответа
        is_eora_related = any(
            kw in answer.lower() 
            for kw in ["eora", "эора", "проект", "решен", "кейс", "технолог", "компания", "разработ"]
        )
        
        # Форматируем ответ
        html_answer = add_html_links(answer, sources)
        
        # Если ответ не о EORA - показываем без ссылок
        if not is_eora_related:
            clean_answer = re.sub(r'<a href=[^>]+>\[(\d+)\]</a>', r'[\1]', html_answer)
            clean_answer = re.sub(r'\[\d+\]', '', clean_answer)
            await processing_msg.edit_text(
                clean_answer, 
                parse_mode=None
            )
        else:
            await processing_msg.edit_text(
                html_answer, 
                parse_mode="HTML",
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"Ошибка обработки: {e!s}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса", parse_mode=None)

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