import os
import logging
from typing import List

class Config:
    """Класс конфигурации для бота"""
    
    def __init__(self):
        # Telegram настройки
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # n8n настройки
        self.N8N_BASE_URL = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
        self.N8N_API_KEY = os.getenv('N8N_API_KEY')
        
        # Безопасность
        allowed_users = os.getenv('ALLOWED_USERS', '')
        self.ALLOWED_USERS = [int(user_id.strip()) for user_id in allowed_users.split(',') if user_id.strip()]
        
        # Логирование
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.LOG_LEVEL = getattr(logging, log_level, logging.INFO)
        
        # Проверка обязательных параметров
        self._validate_config()
    
    def _validate_config(self):
        """Проверка обязательных параметров конфигурации"""
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")
        
        if not self.N8N_API_KEY:
            raise ValueError("N8N_API_KEY не установлен!")
        
        if not self.ALLOWED_USERS:
            raise ValueError("ALLOWED_USERS не установлен!")
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверка, разрешен ли пользователю доступ к боту"""
        return user_id in self.ALLOWED_USERS
