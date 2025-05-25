from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN
from db import (init_db, save_message, get_role, assign_role, get_last_messages,
                get_partner_summary, get_user_summary, create_invite, use_invite, get_pair_id,
                get_pending_invites_older_than)
from gpt import ask_gpt

import asyncio
from telegram import Bot

pending_roles = {}
pending_invites = {}
created_pairs = set()

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

        await asyncio.sleep(3600)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    lowered = message.lower()

    role = get_role(user_id)
    pair_id = get_pair_id(user_id)

    print(f"[DEBUG] user_id: {user_id}, role: {role}, pair_id: {pair_id}")

    # Проверка: если уже назначена роль, но нет пары — позволяем начать беседу
    if role and not pair_id:
        save_message(user_id, None, role, message)
        user_history = [message]
        user_summary = get_user_summary(user_id)
        partner_summary = "(партнёр ещё не присоединился)"

        reply = ask_gpt(
            user_history=user_history,
            partner_summary=partner_summary,
            user_summary=user_summary,
            gender="женский" if role == "wife" else "мужской"
        )

        await update.message.reply_text(reply)
        return

    # Полноценный диалог
    if role and pair_id:
        save_message(user_id, pair_id, role, message)
        user_history = get_last_messages(pair_id)
        user_summary = get_user_summary(user_id)
        partner_summary = get_partner_summary(role, pair_id)

        reply = ask_gpt(
            user_history=user_history,
            partner_summary=partner_summary,
            user_summary=user_summary,
            gender="женский" if role == "wife" else "мужской"
        )

        await update.message.reply_text(reply)
        return

    # Начало регистрации: пользователь без роли и без кода
    if not role and user_id not in pending_roles and user_id not in pending_invites:
        pending_roles[user_id] = True
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("Муж")], [KeyboardButton("Жена")]],
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Выберите роль: Муж или Жена"
        )
        await update.message.reply_text(
            "Привет! Пожалуйста, выбери свою роль:", reply_markup=keyboard
        )
        return

    # Выбор роли — создание инвайта
    if user_id in pending_roles and lowered in ['муж', 'жена']:
        role_value = 'husband' if lowered == 'муж' else 'wife'
        invite_code = f"PAIR{user_id}"
        create_invite(invite_code, user_id)
        assign_role(user_id, role_value, None)
        pending_invites[user_id] = invite_code
        del pending_roles[user_id]

        instruction = (
            f"Отлично! Теперь отправь своему партнёру вот такой код:\n\n"
            f"\"{invite_code}\"\n\n"
            f"🔸 Это и есть код вашей пары. Он должен быть скопирован полностью — вместе со словом PAIR и цифрами. Ничего не менять.\n\n"
            f"👉 Партнёр должен:\n"
            f"1. Перейти в этого же бота (в Telegram)\n"
            f"2. В первом сообщении в чате с ботом просто отправить только этот код — без комментариев, без текста, без смайликов. Только сам код, как есть."
        )

        await update.message.reply_text(instruction)
        return

    # Присоединение по инвайт-коду
    if not role and message.startswith("PAIR"):
        new_pair_id = use_invite(message, user_id)
        if not new_pair_id:
            await update.message.reply_text("Похоже, этот код недействителен. Попробуй ещё раз.")
            return

        pending_roles[user_id] = True
        pending_invites[user_id] = new_pair_id
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("Муж")], [KeyboardButton("Жена")]],
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Выберите роль"
        )
        await update.message.reply_text("Теперь выбери свою роль в отношениях:", reply_markup=keyboard)
        return

    # Завершение присоединения
    if user_id in pending_roles and lowered in ['муж', 'жена'] and user_id in pending_invites:
        role_value = 'husband' if lowered == 'муж' else 'wife'
        pair_id = pending_invites[user_id]
        assign_role(user_id, role_value, pair_id)
        del pending_roles[user_id]
        del pending_invites[user_id]
        await update.message.reply_text("Готово. Теперь можешь начать разговор с ботом.")
        return

    if not role:
        if user_id in pending_invites:
            await update.message.reply_text("Пожалуйста, выбери свою роль, чтобы завершить регистрацию в паре.")
        elif user_id in pending_roles:
            await update.message.reply_text("Пожалуйста, выбери 'Муж' или 'Жена'.")
        else:
            await update.message.reply_text("Пожалуйста, начни с выбора роли или ввода кода приглашения.")
        return


if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    loop = asyncio.get_event_loop()
    loop.create_task(reminder_loop())
    print("Бот запущен...")
    app.run_polling()
