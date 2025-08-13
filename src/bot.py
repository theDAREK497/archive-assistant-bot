import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

@dp.message()
async def handle_message(message: Message):
    await message.answer(f"Привет! Ты написал: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
