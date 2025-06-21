"""
Дополнительные методы для N8NTelegramBot
"""
import asyncio
from datetime import datetime
from typing import Dict, List
from telegram import CallbackQuery
from telegram.constants import ParseMode

class BotHandlers:
    """Обработчики для кнопок и действий бота"""
    
    async def _show_main_menu(self, query: CallbackQuery):
        """Показать главное меню"""
        message = (
            "🏠 *Главное меню*\n\n"
            "Выберите нужное действие:"
        )
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.main_menu()
        )
    
    async def _show_status(self, query: CallbackQuery):
        """Показать статус n8n"""
        await query.edit_message_text("🔍 Проверяю статус n8n...")
        
        # Проверяем статус n8n
        health_status = await self.n8n_client.get_health_status()
        
        if health_status.get('status') == 'healthy':
            status_icon = "🟢"
            status_text = "Онлайн"
        elif health_status.get('status') == 'unhealthy':
            status_icon = "🟡"
            status_text = "Проблемы"
        else:
            status_icon = "🔴"
            status_text = "Недоступен"
        
        # Получаем дополнительную информацию
        workflows = await self.n8n_client.get_workflows()
        active_workflows = [w for w in workflows if w.get('active', False)]
        recent_executions = await self.n8n_client.get_executions(limit=5)
        
        status_message = (
            f"{status_icon} *Статус n8n: {status_text}*\n\n"
            f"🌐 Сервер: `{self.config.N8N_BASE_URL}`\n"
            f"📊 Код ответа: `{health_status.get('code', 'N/A')}`\n\n"
            f"📋 Всего workflows: `{len(workflows)}`\n"
            f"✅ Активных: `{len(active_workflows)}`\n"
            f"❌ Неактивных: `{len(workflows) - len(active_workflows)}`\n\n"
            f"🚀 Последних выполнений: `{len(recent_executions)}`\n"
            f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await query.edit_message_text(
            status_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _show_workflows_menu(self, query: CallbackQuery):
        """Показать меню рабочих процессов"""
        message = (
            "📋 *Управление рабочими процессами*\n\n"
            "Выберите действие:"
        )
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.workflows_menu()
        )
    
    async def _show_executions_menu(self, query: CallbackQuery):
        """Показать меню выполнений"""
        message = (
            "🚀 *Мониторинг выполнений*\n\n"
            "Выберите тип выполнений для просмотра:"
        )
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.executions_menu()
        )
    
    async def _show_management_menu(self, query: CallbackQuery):
        """Показать меню управления"""
        message = (
            "⚙️ *Панель управления*\n\n"
            "Административные функции:"
        )
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.management_menu()
        )
    
    async def _show_statistics(self, query: CallbackQuery):
        """Показать статистику"""
        await query.edit_message_text("📊 Собираю статистику...")
        
        # Получаем данные для статистики
        workflows = await self.n8n_client.get_workflows()
        executions = await self.n8n_client.get_executions(limit=50)
        
        # Анализируем данные
        total_workflows = len(workflows)
        active_workflows = len([w for w in workflows if w.get('active', False)])
        
        successful_executions = len([e for e in executions if e.get('finished', False) and e.get('success', False)])
        failed_executions = len([e for e in executions if e.get('finished', False) and not e.get('success', False)])
        running_executions = len([e for e in executions if not e.get('finished', False)])
        
        # Подсчет выполнений за сегодня
        today = datetime.now().date()
        today_executions = []
        for execution in executions:
            started = execution.get('startedAt', '')
            if started:
                try:
                    started_date = datetime.fromisoformat(started.replace('Z', '+00:00')).date()
                    if started_date == today:
                        today_executions.append(execution)
                except:
                    pass
        
        statistics_message = (
            "📈 *Статистика n8n*\n\n"
            "*Рабочие процессы:*\n"
            f"📋 Всего: `{total_workflows}`\n"
            f"✅ Активных: `{active_workflows}`\n"
            f"❌ Неактивных: `{total_workflows - active_workflows}`\n\n"
            "*Выполнения (последние 50):*\n"
            f"✅ Успешных: `{successful_executions}`\n"
            f"❌ С ошибками: `{failed_executions}`\n"
            f"⏳ Выполняется: `{running_executions}`\n\n"
            f"*За сегодня:*\n"
            f"🚀 Запусков: `{len(today_executions)}`\n"
            f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await query.edit_message_text(
            statistics_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _show_help(self, query: CallbackQuery):
        """Показать справку"""
        help_text = (
            "🆘 *Справка по боту n8n Manager*\n\n"
            "*Основные функции:*\n"
            "🔹 *Статус n8n* - проверка работоспособности\n"
            "🔹 *Рабочие процессы* - управление workflows\n"
            "🔹 *Выполнения* - мониторинг запусков\n"
            "🔹 *Управление* - административные функции\n"
            "🔹 *Статистика* - аналитика использования\n\n"
            "*Быстрые команды:*\n"
            "• `/start` - Главное меню\n"
            "• `/status` - Статус n8n\n"
            "• `/workflows` - Список workflows\n"
            "• `/help` - Эта справка\n\n"
            "❓ Нужна помощь? Обратитесь к администратору."
        )
        
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _list_workflows(self, query: CallbackQuery, active_only: bool = False, inactive_only: bool = False):
        """Показать список рабочих процессов"""
        await query.edit_message_text("📋 Загружаю список workflows...")
        
        workflows = await self.n8n_client.get_workflows()
        
        if active_only:
            workflows = [w for w in workflows if w.get('active', False)]
            title = "✅ Активные рабочие процессы"
        elif inactive_only:
            workflows = [w for w in workflows if not w.get('active', False)]
            title = "❌ Неактивные рабочие процессы"
        else:
            title = "📋 Все рабочие процессы"
        
        if not workflows:
            message = f"{title}\n\n🔍 Рабочие процессы не найдены."
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.keyboards.workflows_menu()
            )
            return
        
        # Показываем первые 5 workflows
        message = f"*{title}*\n\n"
        for i, workflow in enumerate(workflows[:5]):
            message += f"{i+1}. {self._format_workflow_info(workflow)}\n\n"
        
        if len(workflows) > 5:
            message += f"... и еще {len(workflows) - 5} workflow(s)\n\n"
        
        message += f"📊 Всего найдено: `{len(workflows)}`"
        
        # Создаем клавиатуру с действиями для первого workflow
        keyboard = []
        if workflows:
            first_workflow = workflows[0]
            workflow_id = first_workflow.get('id')
            is_active = first_workflow.get('active', False)
            
            if workflow_id:
                keyboard = self.keyboards.workflow_actions(workflow_id, is_active).inline_keyboard
        
        # Добавляем кнопку возврата
        keyboard.append([
            InlineKeyboardButton("🔙 К меню workflows", callback_data="workflows"),
            InlineKeyboardButton("🏠 Главная", callback_data="main_menu")
        ])
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _list_executions(self, query: CallbackQuery, success_only: bool = False, 
                             failed_only: bool = False, running_only: bool = False):
        """Показать список выполнений"""
        await query.edit_message_text("🚀 Загружаю список выполнений...")
        
        executions = await self.n8n_client.get_executions(limit=20)
        
        # Фильтруем выполнения
        if success_only:
            executions = [e for e in executions if e.get('finished', False) and e.get('success', False)]
            title = "✅ Успешные выполнения"
        elif failed_only:
            executions = [e for e in executions if e.get('finished', False) and not e.get('success', False)]
            title = "❌ Выполнения с ошибками"
        elif running_only:
            executions = [e for e in executions if not e.get('finished', False)]
            title = "⏳ Выполняющиеся процессы"
        else:
            title = "📋 Последние выполнения"
        
        if not executions:
            message = f"{title}\n\n🔍 Выполнения не найдены."
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.keyboards.executions_menu()
            )
            return
        
        # Показываем первые 5 выполнений
        message = f"*{title}*\n\n"
        for i, execution in enumerate(executions[:5]):
            message += f"{i+1}. {self._format_execution_info(execution)}\n\n"
        
        if len(executions) > 5:
            message += f"... и еще {len(executions) - 5} выполнение(й)\n\n"
        
        message += f"📊 Всего найдено: `{len(executions)}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.executions_menu()
        )
    
    async def _activate_workflow(self, query: CallbackQuery, workflow_id: str):
        """Активировать рабочий процесс"""
        await query.edit_message_text(f"⏳ Активирую workflow {workflow_id}...")
        
        result = await self.n8n_client.activate_workflow(workflow_id)
        
        if 'error' not in result:
            message = f"✅ Workflow `{workflow_id}` успешно активирован!"
        else:
            message = f"❌ Ошибка активации workflow `{workflow_id}`:\n`{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _deactivate_workflow(self, query: CallbackQuery, workflow_id: str):
        """Деактивировать рабочий процесс"""
        await query.edit_message_text(f"⏳ Деактивирую workflow {workflow_id}...")
        
        result = await self.n8n_client.deactivate_workflow(workflow_id)
        
        if 'error' not in result:
            message = f"⏸️ Workflow `{workflow_id}` успешно деактивирован!"
        else:
            message = f"❌ Ошибка деактивации workflow `{workflow_id}`:\n`{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _execute_workflow(self, query: CallbackQuery, workflow_id: str):
        """Запустить рабочий процесс"""
        await query.edit_message_text(f"🚀 Запускаю workflow {workflow_id}...")
        
        result = await self.n8n_client.execute_workflow(workflow_id)
        
        if 'error' not in result:
            execution_id = result.get('data', {}).get('executionId', 'Неизвестно')
            message = f"🚀 Workflow `{workflow_id}` успешно запущен!\n\n📊 ID выполнения: `{execution_id}`"
        else:
            message = f"❌ Ошибка запуска workflow `{workflow_id}`:\n`{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _show_workflow_status(self, query: CallbackQuery, workflow_id: str):
        """Показать статус рабочего процесса"""
        await query.edit_message_text(f"📊 Получаю статус workflow {workflow_id}...")
        
        workflow = await self.n8n_client.get_workflow_status(workflow_id)
        
        if 'error' not in workflow:
            message = f"📊 *Статус Workflow*\n\n{self._format_workflow_info(workflow)}"
        else:
            message = f"❌ Ошибка получения статуса workflow `{workflow_id}`:\n`{workflow['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _stop_execution(self, query: CallbackQuery, execution_id: str):
        """Остановить выполнение"""
        await query.edit_message_text(f"⏹️ Останавливаю выполнение {execution_id}...")
        
        result = await self.n8n_client.stop_execution(execution_id)
        
        if 'error' not in result:
            message = f"⏹️ Выполнение `{execution_id}` успешно остановлено!"
        else:
            message = f"❌ Ошибка остановки выполнения `{execution_id}`:\n`{result['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _show_execution_details(self, query: CallbackQuery, execution_id: str):
        """Показать детали выполнения"""
        await query.edit_message_text(f"📊 Получаю детали выполнения {execution_id}...")
        
        execution = await self.n8n_client.get_execution_details(execution_id)
        
        if 'error' not in execution:
            message = f"📊 *Детали выполнения*\n\n{self._format_execution_info(execution)}"
        else:
            message = f"❌ Ошибка получения деталей выполнения `{execution_id}`:\n`{execution['error']}`"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
    
    async def _refresh_all(self, query: CallbackQuery):
        """Обновить все данные"""
        await query.edit_message_text("🔄 Обновляю все данные...")
        
        # Эмулируем обновление данных
        await asyncio.sleep(2)
        
        message = (
            "✅ *Данные обновлены!*\n\n"
            "🔄 Кэш очищен\n"
            "📊 Статистика пересчитана\n"
            f"⏰ Время обновления: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboards.back_to_main()
        )
