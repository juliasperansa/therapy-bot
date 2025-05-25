from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN
from db import (init_db, save_message, get_role, assign_role, get_last_messages,
                get_partner_summary, get_user_summary, create_invite, use_invite, get_pair_id)
from gpt import ask_gpt

pending_roles = {}
pending_invites = {}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    lowered = message.lower()

    role = get_role(user_id)
    pair_id = get_pair_id(user_id)

    print(f"[DEBUG] user_id: {user_id}, role: {role}, pair_id: {pair_id}")

    # 1. Если пользователь не в паре и не в процессе регистрации роли
    if not role and user_id not in pending_roles:
        pending_roles[user_id] = True
        keyboard = ReplyKeyboardMarkup([['Муж'], ['Жена']], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Привет! Пожалуйста, выбери свою роль:", reply_markup=keyboard
        )
        return

    # 2. Пользователь выбрал роль (муж или жена)
    elif user_id in pending_roles and lowered in ['муж', 'жена']:
        role_value = 'husband' if lowered == 'муж' else 'wife'
        invite_code = f"PAIR{user_id}"  # простой уникальный код, можно улучшить
        create_invite(invite_code, user_id)
        pending_invites[user_id] = role_value
        del pending_roles[user_id]
        await update.message.reply_text(
            f"Отлично! Теперь отправь этот код своему партнёру, чтобы он присоединился: {invite_code}"
        )
        return

    # 3. Пользователь вводит инвайт-код, чтобы присоединиться
    elif not role and message.startswith("PAIR"):
        pair_id = use_invite(message, user_id)
        if not pair_id:
            await update.message.reply_text("Похоже, этот код недействителен. Попробуй ещё раз.")
            return

        keyboard = ReplyKeyboardMarkup([['Муж'], ['Жена']], one_time_keyboard=True, resize_keyboard=True)
        pending_roles[user_id] = True
        await update.message.reply_text(
            "Теперь выбери свою роль в отношениях:", reply_markup=keyboard
        )
        pending_invites[user_id] = pair_id
        return

    elif user_id in pending_roles and lowered in ['муж', 'жена'] and user_id in pending_invites:
        role_value = 'husband' if lowered == 'муж' else 'wife'
        pair_id = pending_invites[user_id]
        assign_role(user_id, role_value, pair_id)
        del pending_roles[user_id]
        del pending_invites[user_id]
        await update.message.reply_text("Готово. Теперь можешь начать разговор с ботом.")
        return

    # 4. Нормальная работа, когда роль и пара уже есть
    if not role or not pair_id:
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйся через код-приглашение.")
        return

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


if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()
