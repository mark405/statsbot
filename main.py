import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

async def get_stats_by_bot():
    """
    Возвращает статистику по ботам:
    total_users_by_bot: {bot_name: количество пользователей}
    users_by_bot: {bot_name: [(username, last_step), ...]}
    """
    total_users_by_bot = {}
    users_by_bot = {}

    async with Session() as session:
        result = await session.execute(
            text("SELECT bot_name, username, last_step FROM user_progress where bot_name != 'hackbotukr' and bot_name != 'hackbotpolish'")
        )
        rows = result.fetchall()

        for bot_name, username, last_step in rows:
            total_users_by_bot[bot_name] = total_users_by_bot.get(bot_name, 0) + 1
            users_by_bot.setdefault(bot_name, []).append((username, last_step))

    return total_users_by_bot, users_by_bot


# --- commands ---

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("📊 Статистический бот запущен\nКоманда: /stats")


@dp.message(Command("stats"))
async def stats(msg: types.Message):
    bot_totals, bot_users = await get_stats_by_bot()

    if not bot_totals:
        await msg.answer("Нет данных для статистики.")
        return

    # Создаем клавиатуру с кнопками по ботам
    kb = InlineKeyboardMarkup(row_width=2)
    for bot_name in bot_totals.keys():
        kb.add(InlineKeyboardButton(text=bot_name, callback_data=f"bot_stats:{bot_name}"))

    await msg.answer("Выберите бота для просмотра статистики:", reply_markup=kb)


# --- callback для кнопок ---
@dp.callback_query()
async def bot_stats_callback(query: CallbackQuery):
    if not query.data.startswith("bot_stats:"):
        return

    bot_name = query.data.split("bot_stats:")[1]

    bot_totals, bot_users = await get_stats_by_bot()
    users = bot_users.get(bot_name, [])
    total = bot_totals.get(bot_name, 0)

    text_msg = f"🤖 Статистика для бота: {bot_name}\n👥 Всего пользователей: {total}\n"
    text_msg += "📍 Пользователи и их последний шаг:\n"
    if users:
        for username, last_step in users:
            text_msg += f"• {username} — {last_step}\n"
    else:
        text_msg += "Нет данных."

    await query.message.edit_text(text_msg)
    await query.answer()


# --- run ---

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
