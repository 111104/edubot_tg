import os
import asyncio
import httpx
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Сен — EduBot, Astana IT University колледжінің интеллектті оқу ассистентісің.
Сен студенттерге мына модульдер бойынша көмек бересің:
• КМ03 / ПМ03 — Бағдарламалық қамтамасыз ету модульдерін бағдарламалау
• КМ04 / ПМ04 — Web-сайтты жобалау және үздіксіз жұмыс істеуін қамтамасыз ету
• КМ05 / ПМ05 — Бағдарламалық кодтың жұмыс жасау рефакторингін тексеру
• КМ06 — Микроконтроллер негізінде сандық құрылғыларды бағдарламалау
• КМ07 — Мобильді қосымшаларды әзірлеу

ТІЛІҢДІ АНЫҚТА: Студент қай тілде жазса, сол тілде жауап бер.

ПЕДАГОГИКАЛЫҚ СТИЛЬ:
- Дайын жауапты бірден берме — алдымен бағыттаушы сұрақ қой
- Студент қате жасаса — "қате" деме, "ал мынадай жағдайда не болады?" деп сұра
- Тьютор рөлін атқар: бағыттай, түсіндір, тексер
- Жауаптың соңында студентке кері сұрақ қой"""

MODULE_CONTEXTS = {
    "km03": "Қазір КМ03/ПМ03: бағдарламалау (Python/Java, алгоритмдер).",
    "km04": "Қазір КМ04/ПМ04: Web-сайт (HTML, CSS, JavaScript).",
    "km05": "Қазір КМ05/ПМ05: рефакторинг (код сапасы, тестілеу).",
    "km06": "Қазір КМ06: микроконтроллер (Arduino, C/C++).",
    "km07": "Қазір КМ07: мобильді қосымшалар (Flutter/React Native).",
}

user_data = {}

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"history": [], "module": "auto"}
    return user_data[user_id]

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

async def tg(method, **kwargs):
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{BASE_URL}/{method}", json=kwargs, timeout=30)
        return r.json()

async def send_message(chat_id, text, reply_markup=None):
    kwargs = {"chat_id": chat_id, "text": text}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        return await tg("sendMessage", parse_mode="Markdown", **kwargs)
    except Exception:
        return await tg("sendMessage", **kwargs)

async def send_typing(chat_id):
    await tg("sendChatAction", chat_id=chat_id, action="typing")

def module_keyboard():
    return {"inline_keyboard": [
        [{"text": "📘 КМ03 — Бағдарламалау", "callback_data": "km03"},
         {"text": "🌐 КМ04 — Web-сайт", "callback_data": "km04"}],
        [{"text": "🔍 КМ05 — Рефакторинг", "callback_data": "km05"},
         {"text": "🔧 КМ06 — Микроконтроллер", "callback_data": "km06"}],
        [{"text": "📱 КМ07 — Мобильді қосымша", "callback_data": "km07"}],
    ]}

def mode_keyboard():
    return {"inline_keyboard": [
        [{"text": "📖 Тақырып түсіндір", "callback_data": "mode_explain"},
         {"text": "🧪 Тапсырма бер", "callback_data": "mode_task"}],
        [{"text": "🎯 Емтиханға дайындай", "callback_data": "mode_exam"},
         {"text": "🔄 Модуль ауыстыр", "callback_data": "change_module"}],
    ]}

async def ai_response(chat_id, user):
    await send_typing(chat_id)
    try:
        module_ctx = MODULE_CONTEXTS.get(user["module"], "")
        system = SYSTEM_PROMPT + ("\n\n" + module_ctx if module_ctx else "")
        contents = []
        for msg in user["history"][-20:]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["text"])]
            ))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=system),
            contents=contents
        )
        bot_text = response.text
        user["history"].append({"role": "model", "text": bot_text})
        await send_message(chat_id, bot_text, reply_markup=mode_keyboard())
    except Exception as e:
        await send_message(chat_id, f"Қате: {str(e)}")

async def handle_update(update):
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        data = cq["data"]
        user = get_user(cq["from"]["id"])
        await tg("answerCallbackQuery", callback_query_id=cq["id"])
        MODULE_NAMES = {
            "km03": "КМ03 — Бағдарламалау", "km04": "КМ04 — Web-сайт",
            "km05": "КМ05 — Рефакторинг", "km06": "КМ06 — Микроконтроллер",
            "km07": "КМ07 — Мобильді қосымша",
        }
        if data in MODULE_NAMES:
            user["module"] = data
            user["history"] = []
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                text=f"✅ *{MODULE_NAMES[data]}* таңдалды!\n\nНе жасайық?",
                parse_mode="Markdown", reply_markup=mode_keyboard())
        elif data == "change_module":
            user["module"] = "auto"
            user["history"] = []
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                text="📚 *Модуль таңдаңыз:*", parse_mode="Markdown",
                reply_markup=module_keyboard())
        elif data == "mode_explain":
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                text="📖 Қай тақырыпты түсіндірейін? 👇", parse_mode="Markdown")
        elif data == "mode_task":
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                text="🧪 Қай тақырып бойынша тапсырма? 👇", parse_mode="Markdown")
        elif data == "mode_exam":
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                text="🎯 Емтиханға дайындалу! Дайынмысың? 💪", parse_mode="Markdown")
            user["history"].append({"role": "user", "text": "Мені емтиханға дайындай, бірінші сұрақты бер"})
            await ai_response(chat_id, user)
    elif "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = get_user(msg["from"]["id"])
        if "text" not in msg:
            return
        text = msg["text"]
        if text == "/start":
            user["history"] = []
            user["module"] = "auto"
            await send_message(chat_id,
                "👋 *Сәлем! Мен EduBot*\n\nAstana IT University колледжінің AI ассистенті.\n\n📚 *Модуль таңдаңыз:*",
                reply_markup=module_keyboard())
            return
        user["history"].append({"role": "user", "text": text})
        await ai_response(chat_id, user)

async def main():
    print("✅ EduBot іске қосылды!")
    offset = 0
    async with httpx.AsyncClient() as http:
        while True:
            try:
                r = await http.get(f"{BASE_URL}/getUpdates",
                    params={"offset": offset, "timeout": 30}, timeout=40)
                for update in r.json().get("result", []):
                    offset = update["update_id"] + 1
                    asyncio.create_task(handle_update(update))
            except Exception as e:
                print(f"Қате: {e}")
                await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())
