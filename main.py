import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

from dotenv import load_dotenv
from config import Config
from n8n_client import N8NClient
from keyboards import BotKeyboards
from bot_handlers import BotHandlers

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class N8NTelegramBot(BotHandlers):
    """Главный класс Telegram бота для управления n8n"""
    
    def __init__(self):
        self.config = Config()
        self.n8n_client = N8NClient(self.config.N8N_BASE_URL, self.config.N8N_API_KEY or "")
        self.keyboards = BotKeyboards()
        
        # Настройка логирования
        logging.getLogger().setLevel(self.config.LOG_LEVEL)
        
        # Создание приложения бота
        self.application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN or "").build()
        
        # Регистрация обработчиков
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и кнопок"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("workflows", self.workflows_command))
        
        # Обработка нажатий кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
    
    def _check_user_permission(self, user_id: int) -> bool:
        """Проверка прав доступа пользователя"""
        return self.config.is_user_allowed(user_id)
    
    async def _send_unauthorized_message(self, update: Update):
        """Отправка сообщения о недостатке прав"""
        await update.message.reply_text(
            "🚫 *Доступ запрещен!*\n\n"
            "У вас нет прав для использования этого бота.\n"
            "Обратитесь к администратору для получения доступа.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def _format_workflow_info(self, workflow: Dict) -> str:
        """Форматирование информации о рабочем процессе"""
        name = workflow.get('name', 'Без названия')
        workflow_id = workflow.get('id', 'Неизвестно')
        active = workflow.get('active', False)
        status_icon = "✅" if active else "❌"
        
        created = workflow.get('createdAt', '')
        if created:
            try:
                created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created_str = created_date.strftime('%d.%m.%Y %H:%M')
            except:
                created_str = "Неизвестно"
        else:
            created_str = "Неизвестно"
        
        return (
            f"{status_icon} *{name}*\n"
            f"🆔 ID: `{workflow_id}`\n"
            f"📅 Создан: {created_str}\n"
            f"🔄 Статус: {'Активен' if active else 'Неактивен'}"
        )
    
    def _format_execution_info(self, execution: Dict) -> str:
        """Форматирование информации о выполнении"""
        execution_id = execution.get('id', 'Неизвестно')
        workflow_name = execution.get('workflowData', {}).get('name', 'Неизвестный workflow')
        status = execution.get('finished', False)
        success = execution.get('success', False)
        
        if status:
            status_icon = "✅" if success else "❌"
            status_text = "Завершено успешно" if success else "Завершено с ошибкой"
        else:
            status_icon = "⏳"
            status_text = "Выполняется"
        
        started = execution.get('startedAt', '')
        if started:
            try:
                started_date = datetime.fromisoformat(started.replace('Z', '+00:00'))
                started_str = started_date.strftime('%d.%m.%Y %H:%M:%S')
            except:
                started_str = "Неизвестно"
        else:
            started_str = "Неизвестно"
        
        return (
            f"{status_icon} *{workflow_name}*\n"
            f"🆔 ID: `{execution_id}`\n"
            f"⏰ Запущено: {started_str}\n"
            f"📊 Статус: {status_text}"
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await self._send_unauthorized_message(update)
            return
        
        username = update.effective_user.first_name or "Пользователь"
        
        welcome_message = (
            f"🤖 *Добро пожаловать, {username}!*\n\n"
            "🎯 Я помогу вам управлять n8n workflows через Telegram!\n\n"
            "📋 *Возможности:*\n"
            "• 📊 Мониторинг статуса n8n\n"
            "• 🔄 Управление рабочими процессами\n"
            "• 🚀 Запуск и остановка workflows\n"
            "• 📈 Просмотр выполнений\n"
            "• ⚙️ Администрирование системы\n\n"
            "Выберите действие из меню ниже:"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.main_menu()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await self._send_unauthorized_message(update)
            return
        
        help_text = (
            "🆘 *Справка по боту n8n Manager*\n\n"
            "*Команды:*\n"
            "• `/start` - Запуск бота и главное меню\n"
            "• `/help` - Эта справка\n"
            "• `/status` - Быстрая проверка статуса n8n\n"
            "• `/workflows` - Список рабочих процессов\n\n"
            "*Основные функции:*\n"
            "🔹 *Статус n8n* - проверка работоспособности сервера\n"
            "🔹 *Рабочие процессы* - просмотр и управление workflows\n"
            "🔹 *Выполнения* - мониторинг запусков workflows\n"
            "🔹 *Управление* - административные функции\n"
            "🔹 *Статистика* - аналитика использования\n\n"
            "*Быстрые действия:*\n"
            "• Активация/деактивация workflows\n"
            "• Запуск workflows вручную\n"
            "• Остановка выполняющихся процессов\n"
            "• Просмотр логов и ошибок\n\n"
            "❓ Если нужна помощь, обратитесь к администратору."
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status"""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await self._send_unauthorized_message(update)
            return
        
        # Отправляем сообщение о проверке
        status_msg = await update.message.reply_text("🔍 Проверяю статус n8n...")
        
        # Проверяем статус n8n
        health_status = await self.n8n_client.get_health_status()
        
        if health_status.get('status') == 'healthy':
            status_icon = "🟢"
            status_text = "Онлайн"
            color = "🟢"
        elif health_status.get('status') == 'unhealthy':
            status_icon = "🟡"
            status_text = "Проблемы"
            color = "🟡"
        else:
            status_icon = "🔴"
            status_text = "Недоступен"
            color = "🔴"
        
        # Получаем дополнительную информацию
        workflows = await self.n8n_client.get_workflows()
        active_workflows = [w for w in workflows if w.get('active', False)]
        recent_executions = await self.n8n_client.get_executions(limit=5)
        
        status_message = (
            f"{color} *Статус n8n: {status_text}*\n\n"
            f"🌐 Сервер: `{self.config.N8N_BASE_URL}`\n"
            f"📊 Код ответа: `{health_status.get('code', 'N/A')}`\n\n"
            f"📋 Всего workflows: `{len(workflows)}`\n"
            f"✅ Активных: `{len(active_workflows)}`\n"
            f"❌ Неактивных: `{len(workflows) - len(active_workflows)}`\n\n"
            f"🚀 Последних выполнений: `{len(recent_executions)}`\n"
            f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await status_msg.edit_text(
            status_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def workflows_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /workflows"""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await self._send_unauthorized_message(update)
            return
        
        await update.message.reply_text(
            "📋 *Управление рабочими процессами*\n\n"
            "Выберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.workflows_menu()
        )
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await self._send_unauthorized_message(update)
            return
        
        # Показываем главное меню для любого текстового сообщения
        await update.message.reply_text(
            "🤖 Используйте кнопки меню для навигации или команды:\n"
            "/start - Главное меню\n"
            "/help - Справка\n"
            "/status - Статус n8n\n"
            "/workflows - Рабочие процессы",
            reply_markup=self.keyboards.main_menu()
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self._check_user_permission(user_id):
            await query.answer("🚫 Доступ запрещен!")
            return
        
        await query.answer()
        
        data = query.data
        
        # Главное меню
        if data == "main_menu":
            await self._show_main_menu(query)
        elif data == "status":
            await self._show_status(query)
        elif data == "workflows":
            await self._show_workflows_menu(query)
        elif data == "executions":
            await self._show_executions_menu(query)
        elif data == "management":
            await self._show_management_menu(query)
        elif data == "statistics":
            await self._show_statistics(query)
        elif data == "help":
            await self._show_help(query)
        
        # Рабочие процессы
        elif data == "list_workflows":
            await self._list_workflows(query)
        elif data == "active_workflows":
            await self._list_workflows(query, active_only=True)
        elif data == "inactive_workflows":
            await self._list_workflows(query, inactive_only=True)
        
        # Выполнения
        elif data == "recent_executions":
            await self._list_executions(query)
        elif data == "successful_executions":
            await self._list_executions(query, success_only=True)
        elif data == "failed_executions":
            await self._list_executions(query, failed_only=True)
        elif data == "running_executions":
            await self._list_executions(query, running_only=True)
        
        # Действия с workflow
        elif data.startswith("activate_"):
            workflow_id = data.split("_", 1)[1]
            await self._activate_workflow(query, workflow_id)
        elif data.startswith("deactivate_"):
            workflow_id = data.split("_", 1)[1]
            await self._deactivate_workflow(query, workflow_id)
        elif data.startswith("execute_"):
            workflow_id = data.split("_", 1)[1]
            await self._execute_workflow(query, workflow_id)
        elif data.startswith("status_"):
            workflow_id = data.split("_", 1)[1]
            await self._show_workflow_status(query, workflow_id)
        
        # Действия с выполнениями
        elif data.startswith("stop_execution_"):
            execution_id = data.split("_", 2)[2]
            await self._stop_execution(query, execution_id)
        elif data.startswith("execution_details_"):
            execution_id = data.split("_", 2)[2]
            await self._show_execution_details(query, execution_id)
        
        # Управление
        elif data == "refresh_all":
            await self._refresh_all(query)
        
        else:
            await query.edit_message_text("⚠️ Неизвестная команда!")
    
    # Методы для обработки различных действий будут добавлены в следующей части...
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск n8n Telegram бота...")
        logger.info(f"🔗 n8n URL: {self.config.N8N_BASE_URL}")
        logger.info(f"👥 Разрешенные пользователи: {self.config.ALLOWED_USERS}")
        
        self.application.run_polling()

if __name__ == "__main__":
    try:
        bot = N8NTelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        print(f"❌ Ошибка: {e}")
        print("\n💡 Убедитесь что:")
        print("1. Создан файл .env с настройками")
        print("2. Указан корректный TELEGRAM_BOT_TOKEN")
        print("3. Указан корректный N8N_API_KEY")
        print("4. Добавлены ID пользователей в ALLOWED_USERS")
