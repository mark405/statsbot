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
            text("SELECT bot_name, username, last_step FROM user_progress where username != 'hackbotukr' and username != 'hackbotpolish'")
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

    # формируем список рядов кнопок
    buttons = []
    row = []

    for i, bot_name in enumerate(bot_totals.keys(), start=1):
        row.append(
            InlineKeyboardButton(
                text=bot_name,
                callback_data=f"bot_stats:{bot_name}"
            )
        )
        if i % 2 == 0:
            buttons.append(row)
            row = []

    if row:  # если осталась неполная строка
        buttons.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await msg.answer(
        "Выберите бота для просмотра статистики:",
        reply_markup=kb
    )

MAX_LEN = 4000  # safe margin


def split_message(text: str, limit: int = MAX_LEN):
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts

# --- callback для кнопок ---
dp.callback_query()
async def bot_stats_callback(query: CallbackQuery):
    if not query.data.startswith("bot_stats:"):
        return

    bot_name = query.data.split("bot_stats:")[1]

    bot_totals, bot_users = await get_stats_by_bot()
    users = bot_users.get(bot_name, [])
    total = bot_totals.get(bot_name, 0)

    header = (
        f"🤖 Статистика для бота: {bot_name}\n"
        f"👥 Всего пользователей: {total}\n"
        "📍 Пользователи и их последний шаг:\n"
    )

    lines = [f"• {u} — {s}\n" for u, s in users]
    full_text = header + "".join(lines)

    parts = split_message(full_text)

    await query.message.edit_text(parts[0])

    for part in parts[1:]:
        await query.message.answer(part)

    await query.answer()


# --- run ---

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
