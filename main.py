from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN
from db import init_db, save_message, get_role, assign_role, get_last_messages, get_partner_summary, get_user_summary
from gpt import ask_gpt

pending_roles = {}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    lowered = message.lower()

    role = get_role(user_id)
    print(
        f"[DEBUG] user_id: {user_id}, role: {role}, pending_roles: {pending_roles}"
    )

    if not role:
        if user_id not in pending_roles:
            pending_roles[user_id] = True
            keyboard = ReplyKeyboardMarkup([['Муж'], ['Жена']],
                                           one_time_keyboard=True,
                                           resize_keyboard=True)
            await update.message.reply_text(
                "Привет! Пожалуйста, выбери, кто ты:", reply_markup=keyboard)
            return
        elif lowered in ["муж", "жена"]:
            role = "husband" if lowered == "муж" else "wife"
            assign_role(user_id, role)
            del pending_roles[user_id]

            await update.message.reply_text(
                f"Спасибо! Ты зарегистрирован как {'муж' if role == 'husband' else 'жена'}."
            )

            # Вводная инструкция
            await update.message.reply_text(
                "⚠️ Важно: всё, что ты здесь напишешь — конфиденциально. Ничего не сохраняется. Если хочешь сохранить фрагмент — скопируй его сам.\n"
                "❗ Главное правило — будь честен. Если ты будешь искажать или придумывать, ты только отдалишься от понимания себя.\n"
                "Не бойся говорить правду. Это безопасное пространство.\n\n"
                "Я здесь, чтобы помочь. Я не дам тебе советов, я не буду тебя уговаривать. Но я задам тебе такие вопросы, после которых ты увидишь себя по-другому."
            )
            await update.message.reply_text(
                "Расскажи, что сейчас тебе больше всего мешает в ваших отношениях?"
            )
            return
        else:
            await update.message.reply_text(
                "Пожалуйста, выбери одну из опций: Муж или Жена.")
            return

    save_message(user_id, role, message)

    user_history = get_last_messages(user_id)
    user_summary = get_user_summary(user_id)
    partner_summary = get_partner_summary(role)

    reply = ask_gpt(user_history=user_history,
                    partner_summary=partner_summary,
                    user_summary=user_summary,
                    gender="женский" if role == "wife" else "мужской")

    await update.message.reply_text(reply)


if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()
