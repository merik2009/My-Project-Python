from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional

class BotKeyboards:
    """Клавиатуры для Telegram бота"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню бота"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Статус n8n", callback_data="status"),
                InlineKeyboardButton("📋 Рабочие процессы", callback_data="workflows")
            ],
            [
                InlineKeyboardButton("🚀 Выполнения", callback_data="executions"),
                InlineKeyboardButton("⚙️ Управление", callback_data="management")
            ],
            [
                InlineKeyboardButton("📈 Статистика", callback_data="statistics"),
                InlineKeyboardButton("❓ Помощь", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def workflows_menu() -> InlineKeyboardMarkup:
        """Меню управления рабочими процессами"""
        keyboard = [
            [
                InlineKeyboardButton("📋 Список всех", callback_data="list_workflows"),
                InlineKeyboardButton("✅ Активные", callback_data="active_workflows")
            ],
            [
                InlineKeyboardButton("❌ Неактивные", callback_data="inactive_workflows"),
                InlineKeyboardButton("🔍 Поиск", callback_data="search_workflow")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def workflow_actions(workflow_id: str, is_active: bool) -> InlineKeyboardMarkup:
        """Действия для конкретного рабочего процесса"""
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
        
        keyboard.extend([
            [
                InlineKeyboardButton("📊 Статус", callback_data=f"status_{workflow_id}"),
                InlineKeyboardButton("📋 Выполнения", callback_data=f"executions_{workflow_id}")
            ],
            [
                InlineKeyboardButton("🔙 К списку", callback_data="list_workflows"),
                InlineKeyboardButton("🏠 Главная", callback_data="main_menu")
            ]
        ])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def executions_menu() -> InlineKeyboardMarkup:
        """Меню выполнений"""
        keyboard = [
            [
                InlineKeyboardButton("📋 Последние", callback_data="recent_executions"),
                InlineKeyboardButton("✅ Успешные", callback_data="successful_executions")
            ],
            [
                InlineKeyboardButton("❌ Ошибки", callback_data="failed_executions"),
                InlineKeyboardButton("⏳ Выполняющиеся", callback_data="running_executions")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def execution_actions(execution_id: str, status: str) -> InlineKeyboardMarkup:
        """Действия для конкретного выполнения"""
        keyboard = [
            [InlineKeyboardButton("📊 Детали", callback_data=f"execution_details_{execution_id}")]
        ]
        
        if status in ["running", "waiting"]:
            keyboard[0].append(
                InlineKeyboardButton("⏹️ Остановить", callback_data=f"stop_execution_{execution_id}")
            )
        
        keyboard.extend([
            [
                InlineKeyboardButton("🔙 К списку", callback_data="recent_executions"),
                InlineKeyboardButton("🏠 Главная", callback_data="main_menu")
            ]
        ])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def management_menu() -> InlineKeyboardMarkup:
        """Меню управления"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Обновить все", callback_data="refresh_all"),
                InlineKeyboardButton("⏹️ Остановить все", callback_data="stop_all")
            ],
            [
                InlineKeyboardButton("🧹 Очистить логи", callback_data="clear_logs"),
                InlineKeyboardButton("🔧 Настройки", callback_data="settings")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirmation(action: str, item_id: Optional[str] = None) -> InlineKeyboardMarkup:
        """Клавиатура подтверждения действия"""
        callback_confirm = f"confirm_{action}_{item_id}" if item_id else f"confirm_{action}"
        callback_cancel = f"cancel_{action}_{item_id}" if item_id else f"cancel_{action}"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=callback_confirm),
                InlineKeyboardButton("❌ Нет", callback_data=callback_cancel)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Кнопка возврата в главное меню"""
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Пагинация для списков"""
        keyboard = []
        
        # Кнопки навигации
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Пред", callback_data=f"{prefix}_page_{current_page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
        
        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton("След ➡️", callback_data=f"{prefix}_page_{current_page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Кнопка возврата
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        return InlineKeyboardMarkup(keyboard)
