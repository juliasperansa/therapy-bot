from telegram.ext import ApplicationBuilder, MessageHandler, filters
from config import TELEGRAM_TOKEN
from db import init_db
from gpt import ask_gpt
from logic import handle_message
import asyncio

async def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
