#!/usr/bin/env python3
"""
🤖 Простая версия n8n Telegram Bot Manager
Базовая версия без сложной типизации для быстрого запуска
"""

import os
import logging
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from dotenv import load_dotenv
import aiohttp
import requests

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleN8NBot:
    def __init__(self):
        # Конфигурация
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
        self.n8n_api_key = os.getenv('N8N_API_KEY')
        
        # Проверяем обязательные параметры
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле!")
        if not self.n8n_api_key:
            raise ValueError("N8N_API_KEY не установлен в .env файле!")
        
        # Разрешенные пользователи
        allowed_users = os.getenv('ALLOWED_USERS', '')
        if not allowed_users:
            raise ValueError("ALLOWED_USERS не установлен в .env файле!")
        
        self.allowed_users = [int(user_id.strip()) for user_id in allowed_users.split(',') if user_id.strip()]
        
        # Создание приложения
        self.app = Application.builder().token(self.bot_token).build()
        
        # Регистрация обработчиков
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
    
    def check_permission(self, user_id):
        """Проверка прав доступа"""
        return user_id in self.allowed_users
    
    def get_main_keyboard(self):
        """Главная клавиатура"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Статус n8n", callback_data="status"),
                InlineKeyboardButton("📋 Workflows", callback_data="workflows")
            ],
            [
                InlineKeyboardButton("🚀 Выполнения", callback_data="executions"),
                InlineKeyboardButton("📈 Статистика", callback_data="stats")
            ],
            [
                InlineKeyboardButton("❓ Помощь", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_workflow_keyboard(self, workflow_id, is_active):
        """Клавиатура для управления конкретным workflow"""
        keyboard = []
        
        if is_active:
            keyboard.append([
                InlineKeyboardButton("⏸️ Деактивировать", callback_data=f"deactivate_{workflow_id}"),
                InlineKeyboardButton("🚀 Запустить", callback_data=f"execute_{workflow_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("▶️ Активировать", callback_data=f"activate_{workflow_id}"),
                InlineKeyboardButton("🚀 Запустить", callback_data=f"execute_{workflow_id}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 К списку", callback_data="workflows"),
            InlineKeyboardButton("🏠 Главная", callback_data="main")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_back_keyboard(self):
        """Кнопка возврата"""
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main")]]
        return InlineKeyboardMarkup(keyboard)
    
    async def n8n_request(self, endpoint, method='GET'):
        """Запрос к n8n API"""
        url = f"{self.n8n_url}/api/v1/{endpoint}"
        headers = {'X-N8N-API-KEY': self.n8n_api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_n8n_health(self):
        """Проверка здоровья n8n"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.n8n_url}/healthz") as response:
                    return {"status": "healthy" if response.status == 200 else "unhealthy", "code": response.status}
        except:
            return {"status": "unreachable", "error": "Connection failed"}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        
        if not self.check_permission(user_id):
            await update.message.reply_text("🚫 Доступ запрещен!")
            return
        
        username = update.effective_user.first_name or "Пользователь"
        
        welcome_text = f"""🤖 *Добро пожаловать, {username}!*

🎯 Я помогу управлять n8n workflows через Telegram!

*Возможности:*
• 📊 Мониторинг статуса n8n
• 📋 Управление workflows  
• 🚀 Просмотр выполнений
• 📈 Статистика системы

Выберите действие из меню ниже:"""
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user_id = update.effective_user.id
        
        if not self.check_permission(user_id):
            await update.message.reply_text("🚫 Доступ запрещен!")
            return
        
        help_text = """🆘 *Справка по боту*

*Команды:*
• `/start` - Главное меню
• `/help` - Эта справка  
• `/status` - Статус n8n

*Функции:*
🔹 *Статус n8n* - проверка сервера
🔹 *Workflows* - управление процессами
🔹 *Выполнения* - мониторинг запусков
🔹 *Статистика* - аналитика

❓ Нужна помощь? Обратитесь к администратору."""
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        user_id = update.effective_user.id
        
        if not self.check_permission(user_id):
            await update.message.reply_text("🚫 Доступ запрещен!")
            return
        
        status_msg = await update.message.reply_text("🔍 Проверяю статус n8n...")
        
        # Проверяем здоровье n8n
        health = await self.check_n8n_health()
        
        if health.get('status') == 'healthy':
            status_icon = "🟢"
            status_text = "Онлайн"
        else:
            status_icon = "🔴" 
            status_text = "Недоступен"
        
        # Получаем дополнительную информацию
        workflows_data = await self.n8n_request('workflows')
        workflows = workflows_data.get('data', []) if 'error' not in workflows_data else []
        active_workflows = [w for w in workflows if w.get('active', False)]
        
        status_message = f"""{status_icon} *Статус n8n: {status_text}*

🌐 Сервер: `{self.n8n_url}`
📊 Код ответа: `{health.get('code', 'N/A')}`

📋 Всего workflows: `{len(workflows)}`
✅ Активных: `{len(active_workflows)}`  
❌ Неактивных: `{len(workflows) - len(active_workflows)}`

⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"""
        
        await status_msg.edit_text(
            status_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий кнопок"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.check_permission(user_id):
            await query.answer("🚫 Доступ запрещен!")
            return
        
        await query.answer()
        data = query.data
        
        if data == "main":
            await self.show_main_menu(query)
        elif data == "status":
            await self.show_status(query)
        elif data == "workflows":
            await self.show_workflows(query)
        elif data == "executions":
            await self.show_executions(query)
        elif data == "stats":
            await self.show_statistics(query)
        elif data == "help":
            await self.show_help(query)
        # Управление workflow
        elif data.startswith("activate_"):
            workflow_id = data.split("_", 1)[1]
            await self.activate_workflow(query, workflow_id)
        elif data.startswith("deactivate_"):
            workflow_id = data.split("_", 1)[1]
            await self.deactivate_workflow(query, workflow_id)
        elif data.startswith("execute_"):
            workflow_id = data.split("_", 1)[1]
            await self.execute_workflow(query, workflow_id)
        elif data.startswith("activate_") or data.startswith("deactivate_") or data.startswith("execute_"):
            # Обработка действий с workflow
            await self.handle_workflow_action(query, data)
    
    async def show_main_menu(self, query):
        """Показать главное меню"""
        message = """🏠 *Главное меню*

Выберите нужное действие:"""
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_keyboard()
        )
    
    async def show_status(self, query):
        """Показать статус"""
        await query.edit_message_text("🔍 Проверяю статус n8n...")
        
        # Проверяем здоровье
        health = await self.check_n8n_health()
        
        if health.get('status') == 'healthy':
            status_icon = "🟢"
            status_text = "Онлайн"
        else:
            status_icon = "🔴"
            status_text = "Недоступен"
        
        # Получаем workflows
        workflows_data = await self.n8n_request('workflows')
        workflows = workflows_data.get('data', []) if 'error' not in workflows_data else []
        active_workflows = [w for w in workflows if w.get('active', False)]
        
        message = f"""{status_icon} *Статус n8n: {status_text}*

🌐 Сервер: `{self.n8n_url}`
📊 Код: `{health.get('code', 'N/A')}`

📋 Всего workflows: `{len(workflows)}`
✅ Активных: `{len(active_workflows)}`
❌ Неактивных: `{len(workflows) - len(active_workflows)}`

⏰ {datetime.now().strftime('%H:%M:%S')}"""
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def show_workflows(self, query):
        """Показать workflows"""
        await query.edit_message_text("📋 Загружаю workflows...")
        
        workflows_data = await self.n8n_request('workflows')
        
        if 'error' in workflows_data:
            message = f"❌ Ошибка загрузки workflows:\n`{workflows_data['error']}`"
        else:
            workflows = workflows_data.get('data', [])
            
            if not workflows:
                message = "📋 *Workflows*\n\n🔍 Workflows не найдены."
            else:
                message = f"📋 *Workflows* (всего: {len(workflows)})\n\n"
                
                # Ограничиваем количество для удобства отображения
                display_workflows = workflows[:10] if len(workflows) > 10 else workflows
                
                for i, workflow in enumerate(display_workflows):
                    name = workflow.get('name', 'Без названия')
                    active = workflow.get('active', False)
                    status_icon = "✅" if active else "❌"
                    workflow_id = workflow.get('id', 'N/A')
                    
                    message += f"{i+1}. {status_icon} *{name}*\n"
                    message += f"   🆔 `{workflow_id}`\n"
                    message += f"   🔄 {'Активен' if active else 'Неактивен'}\n\n"
                
                if len(workflows) > 10:
                    message += f"... и еще {len(workflows) - 10} workflow(s)\n\n"
                
                # Добавляем кнопки для управления первым workflow как пример
                if workflows:
                    first_workflow = workflows[0]
                    first_id = first_workflow.get('id')
                    first_active = first_workflow.get('active', False)
                    if first_id:
                        await query.edit_message_text(
                            message + f"💡 *Выберите действие для первого workflow:*\n`{first_workflow.get('name', 'Без названия')}`",
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=self.get_workflow_keyboard(first_id, first_active)
                        )
                        return
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def show_executions(self, query):
        """Показать выполнения"""
        await query.edit_message_text("🚀 Загружаю выполнения...")
        
        executions_data = await self.n8n_request('executions?limit=20')
        
        if 'error' in executions_data:
            message = f"❌ Ошибка загрузки выполнений:\n`{executions_data['error']}`"
        else:
            executions = executions_data.get('data', [])
            
            if not executions:
                message = "🚀 *Выполнения*\n\n🔍 Выполнения не найдены."
            else:
                message = f"🚀 *Последние выполнения* ({len(executions)})\n\n"
                
                for i, execution in enumerate(executions):  # Показываем все выполнения
                    finished = execution.get('finished', False)
                    success = execution.get('success', False)
                    
                    if finished:
                        status_icon = "✅" if success else "❌"
                        status_text = "Успешно" if success else "Ошибка"
                    else:
                        status_icon = "⏳"
                        status_text = "Выполняется"
                    
                    started = execution.get('startedAt', '')
                    if started:
                        try:
                            started_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                            started_str = started_dt.strftime('%d.%m %H:%M')
                        except:
                            started_str = "N/A"
                    else:
                        started_str = "N/A"
                    
                    workflow_name = execution.get('workflowData', {}).get('name', 'Неизвестный')
                    
                    message += f"{i+1}. {status_icon} *{workflow_name}*\n"
                    message += f"   ⏰ {started_str}\n"
                    message += f"   📊 {status_text}\n\n"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def show_statistics(self, query):
        """Показать статистику"""
        await query.edit_message_text("📈 Собираю статистику...")
        
        # Получаем данные
        workflows_data = await self.n8n_request('workflows')
        executions_data = await self.n8n_request('executions?limit=50')
        
        workflows = workflows_data.get('data', []) if 'error' not in workflows_data else []
        executions = executions_data.get('data', []) if 'error' not in executions_data else []
        
        # Анализируем workflows
        total_workflows = len(workflows)
        active_workflows = len([w for w in workflows if w.get('active', False)])
        
        # Анализируем выполнения
        successful = len([e for e in executions if e.get('finished', False) and e.get('success', False)])
        failed = len([e for e in executions if e.get('finished', False) and not e.get('success', False)])
        running = len([e for e in executions if not e.get('finished', False)])
        
        # Сегодняшние выполнения
        today = datetime.now().date()
        today_executions = 0
        for execution in executions:
            started = execution.get('startedAt', '')
            if started:
                try:
                    started_date = datetime.fromisoformat(started.replace('Z', '+00:00')).date()
                    if started_date == today:
                        today_executions += 1
                except:
                    pass
        
        message = f"""📈 *Статистика n8n*

*Workflows:*
📋 Всего: `{total_workflows}`
✅ Активных: `{active_workflows}`
❌ Неактивных: `{total_workflows - active_workflows}`

*Выполнения (последние 50):*
✅ Успешных: `{successful}`
❌ С ошибками: `{failed}`
⏳ Выполняется: `{running}`

*За сегодня:*
🚀 Запусков: `{today_executions}`

⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"""
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def show_help(self, query):
        """Показать справку"""
        help_text = """🆘 *Справка по боту*

*Основные функции:*
🔹 *Статус n8n* - проверка сервера
🔹 *Workflows* - управление процессами  
🔹 *Выполнения* - мониторинг запусков
🔹 *Статистика* - аналитика системы

*Команды:*
• `/start` - Главное меню
• `/status` - Статус n8n
• `/help` - Справка

❓ Нужна помощь? Обратитесь к администратору."""
        
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def handle_workflow_action(self, query, action_data):
        """Обработка действий с workflow (активация, деактивация, запуск)"""
        action, workflow_id = action_data.split("_", 1)
        workflow_id = int(workflow_id)
        
        if action == "activate":
            # Активировать workflow
            result = await self.n8n_request(f"workflows/{workflow_id}/activate", "POST")
            success = result.get("active", False)
        elif action == "deactivate":
            # Деактивировать workflow
            result = await self.n8n_request(f"workflows/{workflow_id}/deactivate", "POST")
            success = not result.get("active", False)
        elif action == "execute":
            # Запустить workflow
            result = await self.n8n_request(f"workflows/{workflow_id}/execute", "POST")
            success = result.get("finished", False) and result.get("success", False)
        else:
            success = False
        
        if success:
            await query.answer("✅ Действие выполнено успешно!")
        else:
            await query.answer("❌ Ошибка выполнения действия.")
        
        # Обновляем информацию о workflow
        await self.show_workflows(query)
    
    async def activate_workflow(self, query, workflow_id):
        """Активировать workflow"""
        await query.edit_message_text(f"⏳ Активирую workflow {workflow_id}...")
        
        result = await self.n8n_request(f'workflows/{workflow_id}/activate', 'POST')
        
        if 'error' not in result:
            message = f"✅ *Workflow активирован!*\n\n🆔 ID: `{workflow_id}`\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        else:
            message = f"❌ *Ошибка активации workflow*\n\n🆔 ID: `{workflow_id}`\n📝 Ошибка: `{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def deactivate_workflow(self, query, workflow_id):
        """Деактивировать workflow"""
        await query.edit_message_text(f"⏳ Деактивирую workflow {workflow_id}...")
        
        result = await self.n8n_request(f'workflows/{workflow_id}/deactivate', 'POST')
        
        if 'error' not in result:
            message = f"⏸️ *Workflow деактивирован!*\n\n🆔 ID: `{workflow_id}`\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        else:
            message = f"❌ *Ошибка деактивации workflow*\n\n🆔 ID: `{workflow_id}`\n📝 Ошибка: `{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    async def execute_workflow(self, query, workflow_id):
        """Запустить workflow"""
        await query.edit_message_text(f"🚀 Запускаю workflow {workflow_id}...")
        
        result = await self.n8n_request(f'workflows/{workflow_id}/execute', 'POST')
        
        if 'error' not in result:
            execution_id = result.get('data', {}).get('executionId', 'Неизвестно')
            message = f"🚀 *Workflow запущен!*\n\n🆔 Workflow ID: `{workflow_id}`\n📊 Execution ID: `{execution_id}`\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        else:
            message = f"❌ *Ошибка запуска workflow*\n\n🆔 ID: `{workflow_id}`\n📝 Ошибка: `{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_back_keyboard()
        )
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск n8n Telegram бота...")
        logger.info(f"🔗 n8n URL: {self.n8n_url}")
        logger.info(f"👥 Разрешенные пользователи: {self.allowed_users}")
        
        self.app.run_polling()

if __name__ == "__main__":
    try:
        bot = SimpleN8NBot()
        bot.run()
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        print("\n💡 Проверьте:")
        print("1. Файл .env с настройками")
        print("2. Корректность TELEGRAM_BOT_TOKEN")
        print("3. Корректность N8N_API_KEY")
        print("4. Список ALLOWED_USERS")
