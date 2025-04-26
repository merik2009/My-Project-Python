import os
import sqlite3
import logging
import asyncio
import aiosqlite
import aiohttp
import json
import tempfile
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, InputFile, FSInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
import uuid as uuidlib
import qrcode
from io import BytesIO
import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
XRAY_API_URL = os.getenv("XRAY_API_URL")
XRAY_API_KEY = os.getenv("XRAY_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

VPN_PRICE = 29900  # цена в копейках (299 руб.)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, filename='bot.log',
                    format='%(asctime)s %(levelname)s %(message)s')

async def init_db():
    async with aiosqlite.connect('vpn_users.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_admin INTEGER DEFAULT 0,
            vpn_key TEXT DEFAULT NULL
        )''')
        # Добавляем поле email, если его нет
        try:
            await db.execute('ALTER TABLE users ADD COLUMN email TEXT')
            await db.commit()
        except Exception as e:
            pass  # поле уже есть
        await db.commit()

# --- ReplyKeyboard с командами ---
def get_main_keyboard(is_admin=False):
    buttons = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="💳 Платежи"), KeyboardButton(text="❓ Помощь")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🛠️ Админ"), KeyboardButton(text="📈 Все статусы")])
        buttons.append([KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="🔄 Синхр. пользователей")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@router.message(Command("start"))
async def start(msg: types.Message):
    try:
        username = msg.from_user.username or ""
        async with aiosqlite.connect('vpn_users.db') as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id, username, email) VALUES (?, ?, ?)',
                             (msg.from_user.id, username, None))
            await db.commit()
        user_display = f"@{username}" if username else f"ID: {msg.from_user.id}"
        is_admin = msg.from_user.id in ADMIN_IDS
        welcome = (
            f"👋 Добро пожаловать, {user_display}, в VPN Бот!\n\n"
            "Этот бот поможет вам быстро и удобно приобрести доступ к VPN.\n\n"
            "🔒 Ваш интернет — под защитой!\n\n"
            "Выберите действие ниже или используйте меню команд."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛡️ Выбрать тариф", callback_data="choose_tariff")],
                [InlineKeyboardButton(text="🛠️ Техническая поддержка", callback_data="support")]
            ]
        )
        await msg.answer(welcome, reply_markup=kb)
        await msg.answer("Меню команд:", reply_markup=get_main_keyboard(is_admin))
    except Exception as e:
        logging.error(f"Ошибка в /start: {e}")
        await msg.answer(f"Произошла ошибка: {e}")

@router.callback_query(lambda c: c.data == "support")
async def support(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🛠️ Техническая поддержка:\nСвяжитесь с нами: @your_support_username\nИли напишите на email: support@example.com",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
            ]
        )
    )

@router.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback_query: types.CallbackQuery):
    welcome = (
        "👋 Добро пожаловать в VPN Бот!\n\n"
        "Этот бот поможет вам быстро и удобно приобрести доступ к VPN.\n\n"
        "🔒 Ваш интернет — под защитой!\n\n"
        "Выберите действие ниже:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛡️ Выбрать тариф", callback_data="choose_tariff")],
            [InlineKeyboardButton(text="🛠️ Техническая поддержка", callback_data="support")]
        ]
    )
    await callback_query.message.edit_text(welcome, reply_markup=kb)

# --- VPN тарифы и типы ---
VPN_TYPES = [
    {"id": "vless", "name": "VLESS (рекомендуется)"},
    {"id": "vmess", "name": "VMess"},
    {"id": "trojan", "name": "Trojan"}
]
VPN_PLANS = [
    {"id": "basic", "name": "Базовый", "price": 29900, "period": 30},
    {"id": "standard", "name": "Стандартный", "price": 79900, "period": 90},
    {"id": "premium", "name": "Премиум", "price": 249000, "period": 365}
]

# --- Состояния пользователей (в памяти, для примера) ---
user_states = {}

# --- Выбор типа VPN ---
@router.callback_query(lambda c: c.data == "choose_tariff")
async def choose_vpn_type(callback_query: types.CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=v["name"] + " " + ("🛡️" if v["id"]=="vless" else "🔷" if v["id"]=="vmess" else "⚡"), callback_data=f"vpn_type_{v['id']}")] for v in VPN_TYPES
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]]
    )
    await callback_query.message.edit_text(
        "Выберите тип VPN:", reply_markup=kb
    )

# --- Обработка выбора типа VPN ---
@router.callback_query(lambda c: c.data.startswith("vpn_type_"))
async def select_vpn_type(callback_query: types.CallbackQuery):
    vpn_type = callback_query.data.replace("vpn_type_", "")
    user_states[callback_query.from_user.id] = {"vpn_type": vpn_type}
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['name']} ({p['price']//100}₽) 💳", callback_data=f"vpn_plan_{p['id']}")] for p in VPN_PLANS
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="choose_tariff")]]
    )
    await callback_query.message.edit_text(
        f"Выбран тип: {vpn_type}\nТеперь выберите тариф:", reply_markup=kb
    )

# --- Обработка выбора тарифа ---
@router.callback_query(lambda c: c.data.startswith("vpn_plan_"))
async def select_vpn_plan(callback_query: types.CallbackQuery):
    plan_id = callback_query.data.replace("vpn_plan_", "")
    user_state = user_states.get(callback_query.from_user.id, {})
    user_state["plan_id"] = plan_id
    user_states[callback_query.from_user.id] = user_state
    await callback_query.message.edit_text(
        "Введите ваш email для регистрации:")
    user_state["awaiting_email"] = True

# --- Безопасность: ограничение попыток регистрации/оплаты и логирование подозрительных действий ---
MAX_REG_ATTEMPTS = 5
MAX_PAY_ATTEMPTS = 5
reg_attempts = {}
pay_attempts = {}

# --- Обработка email ---
@router.message(lambda msg: user_states.get(msg.from_user.id, {}).get("awaiting_email"))
async def handle_email(msg: types.Message):
    user_id = msg.from_user.id
    reg_attempts[user_id] = reg_attempts.get(user_id, 0) + 1
    if reg_attempts[user_id] > MAX_REG_ATTEMPTS:
        logging.warning(f"Пользователь {user_id} превысил лимит попыток регистрации. Username: {msg.from_user.username}")
        await msg.answer("❗ Превышено количество попыток регистрации. Попробуйте позже или обратитесь в поддержку.")
        return
    email = msg.text.strip()
    # Проверка на корректный email
    if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
        await msg.answer("❗ Пожалуйста, введите корректный email (например, user@example.com)")
        return
    user_state = user_states.get(msg.from_user.id, {})
    user_state["email"] = email
    user_state["awaiting_email"] = False
    user_states[msg.from_user.id] = user_state
    # Кнопка оплаты
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить выбранный тариф", callback_data="pay_vpn")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="choose_tariff")]
        ]
    )
    await msg.answer(f"✉️ Email {email} сохранён. Теперь вы можете оплатить выбранный тариф:", reply_markup=kb)

# --- Обработка оплаты ---
@router.callback_query(lambda c: c.data == "pay_vpn")
async def process_tariff_buy(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    pay_attempts[user_id] = pay_attempts.get(user_id, 0) + 1
    if pay_attempts[user_id] > MAX_PAY_ATTEMPTS:
        logging.warning(f"Пользователь {user_id} превысил лимит попыток оплаты. Username: {callback_query.from_user.username}")
        await callback_query.message.answer("❗ Превышено количество попыток оплаты. Попробуйте позже или обратитесь в поддержку.")
        return
    user_state = user_states.get(callback_query.from_user.id, {})
    plan_id = user_state.get("plan_id")
    vpn_type = user_state.get("vpn_type")
    email = user_state.get("email")
    plan = next((p for p in VPN_PLANS if p["id"] == plan_id), None)
    if not (plan and vpn_type and email):
        await callback_query.message.answer("Ошибка: не выбран тариф, тип VPN или не введён email. Начните сначала.")
        return
    label = plan["name"]
    price = plan["price"]
    prices = [LabeledPrice(label=label, amount=price)]
    try:
        await bot.send_invoice(
            callback_query.from_user.id,
            title=label,
            description=f"{label} — быстрый и безопасный VPN-доступ.",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="vpn-subscription",
            payload=f"{vpn_type}|{plan_id}|{email}"
        )
    except Exception as e:
        logging.error(f"Ошибка при выставлении счета: {e}")
        await callback_query.message.answer("Ошибка при создании счета. Попробуйте позже.")

@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

async def get_fresh_cookie():
    login_url = "https://vpn.x4bot.ru:8028/login"
    XRAY_USERNAME = os.getenv("XRAY_USERNAME")
    XRAY_PASSWORD = os.getenv("XRAY_PASSWORD")
    login_payload = {"username": XRAY_USERNAME, "password": XRAY_PASSWORD}
    async with aiohttp.ClientSession() as session:
        async with session.post(login_url, json=login_payload) as resp:
            cookies = resp.cookies
            if "3x-ui" in cookies:
                return cookies["3x-ui"].value
    return None

async def create_3xui_user(email, vpn_type, plan_id):
    import uuid as uuidlib
    import json
    import time
    api_url = "https://vpn.x4bot.ru:8028/panel/inbound/addClient"
    client_id = str(uuidlib.uuid4())
    # Определяем срок действия по тарифу
    period_days = 30  # по умолчанию
    if plan_id == "standard":
        period_days = 90
    elif plan_id == "premium":
        period_days = 365
    expiry_ms = int((time.time() + period_days * 24 * 60 * 60) * 1000)
    client = {
        "id": client_id,
        "flow": "xtls-rprx-vision",
        "email": email,
        "remark": email,
        "comment": email,
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": expiry_ms,
        "enable": True,
        "tgId": "",
        "subId": "",
        "reset": 0
    }
    data = {
        "id": "1",
        "settings": json.dumps({"clients": [client]})
    }
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=data, cookies=cookies, headers=headers) as resp:
            text = await resp.text()
            try:
                return json.loads(text)
            except Exception:
                return {"raw": text}

async def get_vless_link(email):
    import asyncio
    api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    await asyncio.sleep(2)  # задержка для обновления clients
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, cookies=cookies) as resp:
            if resp.content_type == 'application/json':
                data = await resp.json()
            else:
                text = await resp.text()
                logging.error(f"Неожиданный ответ от панели: {text}")
                return None
            if not data.get("success"):
                return None
            for inbound in data["obj"]:
                if inbound["protocol"] == "vless":
                    host = "vpn.x4bot.ru"
                    port = inbound["port"]
                    settings = json.loads(inbound["settings"])
                    stream = json.loads(inbound["streamSettings"])
                    pbk = stream["realitySettings"]["settings"]["publicKey"]
                    sni = stream["realitySettings"]["serverNames"][0]
                    sid = stream["realitySettings"]["shortIds"][0]
                    flow = settings["clients"][0].get("flow", "")
                    for client in settings["clients"]:
                        logging.debug(f"Проверка клиента: email={client.get('email')}, remark={client.get('remark')}, id={client.get('id')}")
                        if client.get("email") == email or client.get("remark") == email:
                            uuid = client["id"]
                            link = f"vless://{uuid}@{host}:{port}/?type=tcp&security=reality&pbk={pbk}&fp=random&sni={sni}&sid={sid}&spx=%2F&flow={flow}#VPN_{email.replace('@','_')}"
                            return link
    return None

# --- После оплаты: генерация ссылки для подключения ---
@router.message(lambda msg: msg.successful_payment is not None)
async def successful_payment(msg: types.Message):
    try:
        payload = msg.successful_payment.invoice_payload
        parts = payload.split("|")
        if len(parts) != 3:
            await msg.answer(f"Ошибка: некорректный payload ({payload}). Обратитесь в поддержку.")
            logging.error(f"Некорректный payload после оплаты: {payload}")
            return
        vpn_type, plan_id, email = parts
        # --- Создание пользователя ---
        create_result = await create_3xui_user(email, vpn_type, plan_id)
        if not create_result.get("success"):
            await msg.answer(f"Ошибка создания пользователя: {create_result.get('msg')}")
            return
        # --- Получение ссылки ---
        link = await get_vless_link(email)
        if link:
            # Сохраняем ссылку и email в БД только при успешной выдаче
            async with aiosqlite.connect('vpn_users.db') as db:
                await db.execute('UPDATE users SET vpn_key=?, email=? WHERE user_id=?', (link, email, msg.from_user.id))
                # Сохраняем оплату
                import time
                plan = next((p for p in VPN_PLANS if p["id"] == plan_id), None)
                expiry_time = 0
                # Получаем expiryTime из панели, если возможно
                api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
                cookie_val = await get_fresh_cookie()
                cookies = {"3x-ui": cookie_val} if cookie_val else {}
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, cookies=cookies) as resp:
                        if resp.content_type == 'application/json':
                            data = await resp.json()
                            for inbound in data["obj"]:
                                if inbound["protocol"] == "vless":
                                    settings = json.loads(inbound["settings"])
                                    for client in settings["clients"]:
                                        if client.get("email") == email or client.get("remark") == email:
                                            expiry_time = client.get("expiryTime", 0)
                                            break
                await db.execute('''CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT,
                    plan_id TEXT,
                    amount INTEGER,
                    paid_at INTEGER,
                    expiry_time INTEGER
                )''')
                await db.execute('INSERT INTO payments (user_id, email, plan_id, amount, paid_at, expiry_time) VALUES (?, ?, ?, ?, ?, ?)',
                    (msg.from_user.id, email, plan_id, plan["price"] if plan else 0, int(time.time()), expiry_time))
                await db.commit()
            # Генерация QR-кода и отправка через временный файл
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(link)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp, format="PNG")
                tmp_path = tmp.name
            photo = FSInputFile(tmp_path, filename="vpn_qr.png")
            await msg.answer_photo(photo, caption=f"📱 QR-код для подключения к VPN\n\n🔗 Ссылка:\n<code>{link}</code>", parse_mode="HTML")
            os.remove(tmp_path)
            await msg.answer("📊 Для просмотра статистики используйте команду /stats")
        else:
            await msg.answer("Пользователь создан, но ссылка не найдена. Обратитесь в поддержку.")
    except Exception as e:
        logging.error(f"Ошибка при выдаче ссылки: {e}")
        await msg.answer(f"Ошибка при выдаче ссылки: {e}. Обратитесь в поддержку.")

@router.message(Command("stats"))
async def stats(msg: types.Message):
    email = user_states.get(msg.from_user.id, {}).get("email")
    if not email:
        # Пробуем взять email из базы
        async with aiosqlite.connect('vpn_users.db') as db:
            async with db.execute('SELECT email FROM users WHERE user_id=?', (msg.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    email = row[0]
    if not email:
        await msg.answer("Сначала зарегистрируйтесь и оплатите подписку.")
        return
    api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, cookies=cookies) as resp:
            if resp.content_type == 'application/json':
                data = await resp.json()
            else:
                await msg.answer("Ошибка получения статистики: панель недоступна.")
                return
            for inbound in data["obj"]:
                if inbound["protocol"] == "vless":
                    settings = json.loads(inbound["settings"])
                    for client in settings["clients"]:
                        if client.get("email") == email or client.get("remark") == email:
                            used = client.get("up", 0) + client.get("down", 0)
                            total = client.get("totalGB", 0)
                            await msg.answer(f"📊 Статистика по вашему VPN:\n\nТрафик использовано: {used // (1024**3)} ГБ\nЛимит: {total // (1024**3) if total else 'Безлимит'} ГБ\nАккаунт: {email}")
                            return
            await msg.answer("Не удалось найти статистику по вашему аккаунту. Обратитесь в поддержку.")

# --- Админ-панель ---
@router.message(lambda msg: msg.text and msg.text.strip() == "/admin")
async def admin_panel(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Нет доступа.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Список пользователей", callback_data="admin_users")],
            [InlineKeyboardButton(text="Выдать ключ", callback_data="admin_give_key")],
            [InlineKeyboardButton(text="Удалить пользователя", callback_data="admin_delete_user")]
        ]
    )
    await msg.answer("Админ-панель:", reply_markup=kb)

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Нет доступа.", show_alert=True)
        return
    async with aiosqlite.connect('vpn_users.db') as db:
        async with db.execute('SELECT user_id, username, vpn_key FROM users') as cursor:
            users = await cursor.fetchall()
    text = "Пользователи:\n" + "\n".join([f"ID: {u[0]}, @{u[1]}, ключ: {u[2] or '-'}" for u in users])
    await callback_query.message.answer(text)

@router.callback_query(lambda c: c.data == "admin_give_key")
async def admin_give_key(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Нет доступа.", show_alert=True)
        return
    await callback_query.message.answer("Введите ID пользователя для выдачи ключа (через пробел ключ):\nПример: 123456789 myvpnkey")

@router.callback_query(lambda c: c.data == "admin_delete_user")
async def admin_delete_user(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Нет доступа.", show_alert=True)
        return
    await callback_query.message.answer("Введите ID пользователя для удаления:")

@router.message(lambda msg: msg.from_user.id in ADMIN_IDS and len(msg.text.split()) == 2 and msg.text.split()[0].isdigit() and not user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def admin_set_key(msg: types.Message):
    try:
        user_id, key = msg.text.split()
        async with aiosqlite.connect('vpn_users.db') as db:
            await db.execute('UPDATE users SET vpn_key=? WHERE user_id=?', (key, int(user_id)))
            await db.commit()
        await msg.answer(f"Ключ {key} выдан пользователю {user_id}")
    except Exception as e:
        logging.error(f"Ошибка выдачи ключа: {e}")
        await msg.answer("Ошибка при выдаче ключа.")

@router.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.text and msg.text.strip().isdigit() and len(msg.text.strip()) > 5)
async def admin_delete_user_id(msg: types.Message):
    user_id = int(msg.text.strip())
    async with aiosqlite.connect('vpn_users.db') as db:
        await db.execute('DELETE FROM users WHERE user_id=?', (user_id,))
        await db.commit()
    await msg.answer(f"Пользователь с ID {user_id} удалён из базы.")

@router.message(lambda msg: msg.text and msg.text.strip() == "/sync_users")
async def sync_users(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Нет доступа.")
        return
    await msg.answer("⏳ Синхронизация информации о пользователях с панелью...")
    # Получаем список клиентов из панели
    api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    panel_clients = dict()  # email/remark -> dict с данными
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, cookies=cookies) as resp:
            if resp.content_type == 'application/json':
                data = await resp.json()
            else:
                await msg.answer("Ошибка получения данных с панели.")
                return
            for inbound in data["obj"]:
                if inbound["protocol"] == "vless":
                    settings = json.loads(inbound["settings"])
                    for client in settings["clients"]:
                        key = client.get("email") or client.get("remark")
                        if key:
                            panel_clients[key] = client
    # Только обновляем информацию о пользователях в базе (не удаляем)
    updated = 0
    async with aiosqlite.connect('vpn_users.db') as db:
        async with db.execute('SELECT user_id, username, email FROM users') as cursor:
            users = await cursor.fetchall()
        for user_id, username, email in users:
            if email:
                client = panel_clients.get(email)
                if client:
                    # Найти inbound, где есть этот client
                    link = None
                    for inbound in data["obj"]:
                        if inbound["protocol"] == "vless":
                            settings = json.loads(inbound["settings"])
                            stream = json.loads(inbound["streamSettings"])
                            pbk = stream["realitySettings"]["settings"]["publicKey"]
                            sni = stream["realitySettings"]["serverNames"][0]
                            sid = stream["realitySettings"]["shortIds"][0]
                            host = "vpn.x4bot.ru"
                            port = inbound["port"]
                            flow = client.get("flow", "")
                            for c in settings["clients"]:
                                if (c.get("email", "").lower() == email.lower() or c.get("remark", "").lower() == email.lower()):
                                    uuid = c["id"]
                                    link = f"vless://{uuid}@{host}:{port}/?type=tcp&security=reality&pbk={pbk}&fp=random&sni={sni}&sid={sid}&spx=%2F&flow={flow}#VPN_{email.replace('@','_')}"
                                    break
                            if link:
                                break
                    if link:
                        await db.execute('UPDATE users SET vpn_key=? WHERE user_id=?', (link, user_id))
                        updated += 1
        await db.commit()
    await msg.answer(f"✅ Синхронизация завершена. Обновлено пользователей: {updated}")

@router.message(Command("profile"))
async def profile(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect('vpn_users.db') as db:
        async with db.execute('SELECT username, email, vpn_key FROM users WHERE user_id=?', (user_id,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        await msg.answer("Вы ещё не зарегистрированы. Используйте /start.")
        return
    username, email, vpn_key = row
    # Получаем данные из панели
    api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    import asyncio
    await asyncio.sleep(1)
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, cookies=cookies) as resp:
            if resp.content_type == 'application/json':
                data = await resp.json()
            else:
                await msg.answer("Ошибка получения данных с панели.")
                return
            found = False
            for inbound in data["obj"]:
                if inbound["protocol"] == "vless":
                    settings = json.loads(inbound["settings"])
                    client_stats = {str(cs.get("email")).strip().lower(): cs for cs in inbound.get("clientStats", [])}
                    for client in settings["clients"]:
                        logging.debug(f"PROFILE DEBUG: email={client.get('email')}, remark={client.get('remark')}, id={client.get('id')}, up={client.get('up')}, down={client.get('down')}, expiryTime={client.get('expiryTime')}, enable={client.get('enable')}")
                        # Сравниваем email и remark без учёта регистра и пробелов
                        email_db = (email or '').strip().lower()
                        email_client = (client.get("email", "") or '').strip().lower()
                        remark_client = (client.get("remark", "") or '').strip().lower()
                        if email_db and (email_client == email_db or remark_client == email_db):
                            found = True
                            # Берём трафик и expiryTime из clientStats, если есть
                            stat = client_stats.get(email_client) or client_stats.get(remark_client)
                            if stat:
                                used = (stat.get("up", 0) or 0) + (stat.get("down", 0) or 0)
                                expiry = stat.get("expiryTime", 0)
                                total = stat.get("total", 0) or client.get("totalGB", 0)
                            else:
                                used = client.get("up", 0) + client.get("down", 0)
                                expiry = client.get("expiryTime", 0)
                                total = client.get("totalGB", 0)
                            import datetime
                            if expiry and expiry != 0:
                                dt = datetime.datetime.fromtimestamp(expiry/1000)
                                expiry_str = dt.strftime("%d.%m.%Y %H:%М")
                            else:
                                expiry_str = "Без ограничения"
                            status = "✅ Активен" if client.get("enable") else "❌ Отключён"
                            link = vpn_key or "-"
                            if link and link != "-":
                                qr = qrcode.QRCode(box_size=10, border=2)
                                qr.add_data(link)
                                qr.make(fit=True)
                                img = qr.make_image(fill_color="black", back_color="white")
                                import tempfile, os
                                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                                    img.save(tmp, format="PNG")
                                    tmp_path = tmp.name
                                from aiogram.types import FSInputFile
                                photo = FSInputFile(tmp_path, filename="vpn_qr.png")
                                await msg.answer_photo(photo, caption=f"📱 Ваш QR-код для подключения", parse_mode="HTML")
                                os.remove(tmp_path)
                            await msg.answer(
                                f"👤 <b>Личный кабинет</b>\n"
                                f"Имя: @{username if username else '-'}\n"
                                f"Email: {email or '-'}\n"
                                f"Статус: {status}\n"
                                f"Дата окончания: {expiry_str}\n"
                                f"Лимит: {total // (1024**3) if total else 'Безлимит'} ГБ\n"
                                f"Трафик использовано: {used // (1024**3)} ГБ\n"
                                f"Ссылка: <code>{link}</code>\n",
                                parse_mode="HTML"
                            )
                            return
            if not found:
                await msg.answer("Ваш аккаунт не найден в панели. Обратитесь в поддержку.")

@router.message(Command("allstats"))
async def all_stats(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Нет доступа.")
        return
    api_url = "https://vpn.x4bot.ru:8028/panel/api/inbounds/list"
    cookie_val = await get_fresh_cookie()
    cookies = {"3x-ui": cookie_val} if cookie_val else {}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, cookies=cookies) as resp:
            if resp.content_type != 'application/json':
                await msg.answer("Ошибка получения данных с панели.")
                return
            data = await resp.json()
            users_stats = []
            total_traffic = 0
            active = 0
            inactive = 0
            for inbound in data["obj"]:
                if inbound["protocol"] == "vless":
                    settings = json.loads(inbound["settings"])
                    client_stats = {str(cs.get("email")).strip().lower(): cs for cs in inbound.get("clientStats", [])}
                    for client in settings["clients"]:
                        email = client.get("email") or client.get("remark") or "-"
                        email_key = str(email).strip().lower()
                        stat = client_stats.get(email_key)
                        if stat:
                            used = (stat.get("up", 0) or 0) + (stat.get("down", 0) or 0)
                        else:
                            used = (client.get("up", 0) or 0) + (client.get("down", 0) or 0)
                        total_traffic += used
                        enable = client.get("enable", False)
                        users_stats.append({
                            "email": email,
                            "used": used,
                            "enable": enable
                        })
                        if enable:
                            active += 1
                        else:
                            inactive += 1
            # Топ-10 по использованию
            top10 = sorted(users_stats, key=lambda x: x["used"], reverse=True)[:10]
            top10_str = "\n".join([
                f"{i+1}. {u['email']}: {u['used']//(1024**3)} ГБ" for i, u in enumerate(top10)
            ])
            text = (
                f"📊 <b>Общая статистика</b>\n"
                f"Всего пользователей: {len(users_stats)}\n"
                f"Активных: {active} | Неактивных: {inactive}\n"
                f"Суммарный трафик: {total_traffic // (1024**3)} ГБ\n\n"
                f"<b>Топ-10 по использованию:</b>\n{top10_str if top10_str else 'Нет данных'}"
            )
            await msg.answer(text, parse_mode="HTML")

@router.message(Command("help"))
async def help_command(msg: types.Message):
    is_admin = msg.from_user.id in ADMIN_IDS
    text = (
        "<b>Справка по командам бота:</b>\n\n"
        "<b>/start</b> — Запуск бота и приветствие.\n"
        "<b>/help</b> — Показать это справочное сообщение.\n"
        "<b>/profile</b> — Личный кабинет: статус, дата окончания, лимит, ссылка, QR-код, статистика.\n"
        "<b>/stats</b> — Статистика по вашему VPN (трафик, лимит).\n"
        "<b>/payments</b> — История ваших оплат и дат окончания подписки.\n"
        "<b>/allstats</b> — (Админ) Общая статистика по всем пользователям.\n"
        "<b>/admin</b> — (Админ) Открыть админ-панель.\n"
        "<b>/sync_users</b> — (Админ) Синхронизировать информацию о пользователях с панелью.\n"
        "<b>/broadcast</b> — (Админ) Массовая рассылка сообщения всем пользователям.\n"
        "\n<b>Основные действия доступны также через кнопки меню!</b>\n\n"
        "Если возникли вопросы — используйте /support или кнопку поддержки."
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))

# --- История платежей ---
@router.message(Command("payments"))
async def payments_history(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect('vpn_users.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            plan_id TEXT,
            amount INTEGER,
            paid_at INTEGER,
            expiry_time INTEGER
        )''')
        await db.commit()
        async with db.execute('SELECT email, plan_id, amount, paid_at, expiry_time FROM payments WHERE user_id=? ORDER BY paid_at DESC', (user_id,)) as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await msg.answer("У вас нет истории оплат.")
        return
    text = "<b>История платежей:</b>\n"
    for email, plan_id, amount, paid_at, expiry_time in rows:
        import datetime
        paid_str = datetime.datetime.fromtimestamp(paid_at).strftime("%d.%m.%Y %H:%М")
        expiry_str = datetime.datetime.fromtimestamp(expiry_time/1000).strftime("%d.%м.%Y %H:%М") if expiry_time else "-"
        text += f"Тариф: {plan_id}, Email: {email}\nСумма: {amount//100}₽\nОплачено: {paid_str}\nДействует до: {expiry_str}\n---\n"
    await msg.answer(text, parse_mode="HTML")

# --- Массовая рассылка ---
@router.message(Command("broadcast"))
async def broadcast(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Нет доступа.")
        return
    await msg.answer("Введите текст рассылки:")
    user_states[msg.from_user.id] = {"awaiting_broadcast": True}

@router.message(lambda msg: user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def do_broadcast(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    text = msg.text
    user_states[msg.from_user.id]["awaiting_broadcast"] = False
    # Получаем всех пользователей
    async with aiosqlite.connect('vpn_users.db') as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            users = await cursor.fetchall()
    count = 0
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, f"📢 {text}")
            count += 1
        except Exception as e:
            logging.error(f"Ошибка рассылки пользователю {user_id}: {e}")
    await msg.answer(f"Рассылка завершена. Сообщение отправлено {count} пользователям.")

# --- Обработка кнопок без слеша ---
@router.message(lambda msg: msg.text == "👤 Профиль" and not user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def btn_profile(msg: types.Message):
    await profile(msg)

@router.message(lambda msg: msg.text == "📊 Статистика" and not user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def btn_stats(msg: types.Message):
    await stats(msg)

@router.message(lambda msg: msg.text == "💳 Платежи" and not user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def btn_payments(msg: types.Message):
    await payments_history(msg)

@router.message(lambda msg: msg.text == "❓ Помощь" and not user_states.get(msg.from_user.id, {}).get("awaiting_broadcast"))
async def btn_help(msg: types.Message):
    await help_command(msg)

@router.message(lambda msg: msg.text == "🛠️ Админ" and msg.from_user.id in ADMIN_IDS)
async def btn_admin(msg: types.Message):
    await admin_panel(msg)

@router.message(lambda msg: msg.text == "📈 Все статусы" and msg.from_user.id in ADMIN_IDS)
async def btn_allstats(msg: types.Message):
    await all_stats(msg)

@router.message(lambda msg: msg.text == "📢 Рассылка" and msg.from_user.id in ADMIN_IDS)
async def btn_broadcast(msg: types.Message):
    await broadcast(msg)

@router.message(lambda msg: msg.text == "🔄 Синхр. пользователей" and msg.from_user.id in ADMIN_IDS)
async def btn_sync_users(msg: types.Message):
    await sync_users(msg)

async def main():
    await init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())