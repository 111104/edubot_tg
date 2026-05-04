import os
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== КОНФИГУРАЦИЯ =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = """Сен — EduBot, Astana IT University колледжінің интеллектті оқу ассистентісің.
Сен студенттерге мына модульдер бойынша көмек бересің:

• КМ03 / ПМ03 — Бағдарламалық қамтамасыз ету модульдерін бағдарламалау
• КМ04 / ПМ04 — Web-сайтты жобалау және үздіксіз жұмыс істеуін қамтамасыз ету
• КМ05 / ПМ05 — Бағдарламалық кодтың жұмыс жасау рефакторингін тексеру
• КМ06 — Микроконтроллер негізінде сандық құрылғыларды бағдарламалау
• КМ07 — Мобильді қосымшаларды әзірлеу

ТІЛІҢДІ АНЫҚТА:
Студент қай тілде жазса, сол тілде жауап бер (қазақша, орысша немесе ағылшынша).

ПЕДАГОГИКАЛЫҚ СТИЛЬ (ОТЕ МАҢЫЗДЫ):
- Дайын жауапты бірден берме — алдымен бағыттаушы сұрақ қой
- Студент қате жасаса — "қате" деме, "ал мынадай жағдайда не болады?" деп сұра
- Әр түсіндірмеден кейін тексеру сұрағын қой
- Студент тұрып қалса — жауапты бөліп-бөліп бер, бірден емес
- Тьютор рөлін атқар: бағыттай, түсіндір, тексер

ЖАУАП ФОРМАТЫ:
- Қысқа және нақты жаз
- Telegram форматын қолдан: *жирный*, _курсив_, `код`
- Жауаптың соңында студентке кері сұрақ қой"""

MODULE_CONTEXTS = {
    "km03": "Қазір КМ03/ПМ03 модулі: бағдарламалық қамтамасыз ету модульдерін бағдарламалау (алгоритмдер, деректер құрылымы, Python/Java).",
    "km04": "Қазір КМ04/ПМ04 модулі: Web-сайтты жобалау (HTML, CSS, JavaScript, фреймворктер).",
    "km05": "Қазір КМ05/ПМ05 модулі: бағдарламалық кодтың рефакторингін тексеру (код сапасы, тестілеу, оңтайландыру).",
    "km06": "Қазір КМ06 модулі: микроконтроллер негізінде сандық құрылғыларды бағдарламалау (Arduino, C/C++).",
    "km07": "Қазір КМ07 модулі: мобильді қосымшаларды әзірлеу (Android/iOS, Flutter немесе React Native).",
}

# Пайдаланушы деректерін сақтау
user_data = {}

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "history": [],
            "module": "auto"
        }
    return user_data[user_id]

def get_module_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📘 КМ03 — Бағдарламалау", callback_data="km03"),
            InlineKeyboardButton("🌐 КМ04 — Web-сайт", callback_data="km04"),
        ],
        [
            InlineKeyboardButton("🔍 КМ05 — Рефакторинг", callback_data="km05"),
            InlineKeyboardButton("🔧 КМ06 — Микроконтроллер", callback_data="km06"),
        ],
        [
            InlineKeyboardButton("📱 КМ07 — Мобильді қосымша", callback_data="km07"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_mode_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📖 Тақырып түсіндір", callback_data="mode_explain"),
            InlineKeyboardButton("🧪 Тапсырма бер", callback_data="mode_task"),
        ],
        [
            InlineKeyboardButton("🎯 Емтиханға дайындай", callback_data="mode_exam"),
            InlineKeyboardButton("🔄 Модуль ауыстыр", callback_data="change_module"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["history"] = []
    user["module"] = "auto"

    await update.message.reply_text(
        "👋 *Сәлем! Мен EduBot — AI оқу ассистентің*\n\n"
        "Astana IT University колледжінің студенттеріне арналған интеллектті көмекші.\n\n"
        "📚 *Қай модуль бойынша жұмыс жасаймыз?*",
        parse_mode="Markdown",
        reply_markup=get_module_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    MODULE_NAMES = {
        "km03": "КМ03 — Бағдарламалау модульдері",
        "km04": "КМ04 — Web-сайт",
        "km05": "КМ05 — Рефакторинг",
        "km06": "КМ06 — Микроконтроллер",
        "km07": "КМ07 — Мобильді қосымша",
    }

    if data in MODULE_NAMES:
        user["module"] = data
        user["history"] = []
        await query.edit_message_text(
            f"✅ *{MODULE_NAMES[data]}* модулі таңдалды!\n\nНе жасайық?",
            parse_mode="Markdown",
            reply_markup=get_mode_keyboard()
        )

    elif data == "change_module":
        user["module"] = "auto"
        user["history"] = []
        await query.edit_message_text(
            "📚 *Модуль таңдаңыз:*",
            parse_mode="Markdown",
            reply_markup=get_module_keyboard()
        )

    elif data == "mode_explain":
        await query.edit_message_text(
            "📖 *Тақырып түсіндіру режимі*\n\nҚай тақырыпты түсіндірейін? Жаз 👇",
            parse_mode="Markdown"
        )

    elif data == "mode_task":
        await query.edit_message_text(
            "🧪 *Практикалық тапсырма режимі*\n\nҚай тақырып бойынша тапсырма алғың келеді? Жаз 👇",
            parse_mode="Markdown"
        )

    elif data == "mode_exam":
        await query.edit_message_text(
            "🎯 *Емтиханға дайындалу режимі*\n\nДайынмысың? Сұрақ беремін! 💪",
            parse_mode="Markdown"
        )
        user["history"].append({"role": "user", "parts": ["Мені емтиханға дайындай, бірінші сұрақты бер"]})
        await send_ai_response(query.message, user)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text

    user["history"].append({"role": "user", "parts": [text]})

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    await send_ai_response(update.message, user)

async def send_ai_response(message, user):
    try:
        module_ctx = MODULE_CONTEXTS.get(user["module"], "")
        system = SYSTEM_PROMPT + ("\n\n" + module_ctx if module_ctx else "")

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system
        )

        # Gemini history форматы
        history = user["history"][:-1] if len(user["history"]) > 1 else []
        chat = model.start_chat(history=history)

        last_msg = user["history"][-1]["parts"][0]
        response = chat.send_message(last_msg)
        bot_text = response.text

        user["history"].append({"role": "model", "parts": [bot_text]})

        # Telegram Markdown қателерін болдырмау үшін
        try:
            await message.reply_text(
                bot_text,
                parse_mode="Markdown",
                reply_markup=get_mode_keyboard()
            )
        except Exception:
            await message.reply_text(
                bot_text,
                reply_markup=get_mode_keyboard()
            )

    except Exception as e:
        await message.reply_text(
            f"⚠️ Қате: {str(e)}\n\nКейінірек байқап көр."
        )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ EduBot (Gemini) іске қосылды!")
    app.run_polling()

if __name__ == "__main__":
    main()
