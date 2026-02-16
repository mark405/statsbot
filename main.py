import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DB_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

bot = Bot(TOKEN)
dp = Dispatcher()


# --- helpers ---

async def get_stats():
    async with Session() as session:
        # общее количество пользователей
        total_users = await session.execute(
            text("SELECT COUNT(*) FROM user_progress")
        )
        total_users = total_users.scalar()

        # список всех пользователей с ником и последним шагом
        user_list = await session.execute(
            text("SELECT username, last_step FROM user_progress ORDER BY last_step DESC")
        )
        user_list = user_list.fetchall()

    return total_users, user_list


# --- commands ---

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("📊 Статистический бот запущен\nКоманда: /stats")


@dp.message(Command("stats"))
async def stats(msg: types.Message):
    total, users = await get_stats()

    text_msg = f"📈 Статистика\n\n👥 Всего пользователей: {total}\n\n"

    text_msg += "📍 Пользователи и их последний шаг:\n"
    if users:
        for username, last_step in users:
            text_msg += f"• {username} — {last_step}\n"
    else:
        text_msg += "нет данных"

    await msg.answer(text_msg)


# --- run ---

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())