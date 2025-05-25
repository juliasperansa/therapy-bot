import asyncio
import datetime
from db import get_pending_invites_older_than
from telegram import Bot
from config import TELEGRAM_TOKEN

bot = Bot(token=TELEGRAM_TOKEN)

async def reminder_loop():
    while True:
        print("[REMINDER] Checking for old invites...")
        invites = get_pending_invites_older_than(24)
        for inviter_id, invite_code in invites:
            try:
                await bot.send_message(
                    chat_id=inviter_id,
                    text=(f"Напоминаю: прошло больше суток, а ваш партнёр всё ещё не присоединился к паре.\n\n"
                          f"Если нужно, отправьте ему код ещё раз: \"{invite_code}\"")
                )
            except Exception as e:
                print(f"[ERROR] Не удалось отправить сообщение пользователю {inviter_id}: {e}")

        await asyncio.sleep(3600)  # ждать 1 час

if __name__ == "__main__":
    asyncio.run(reminder_loop())
