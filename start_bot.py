#!/usr/bin/env python3
"""
🤖 n8n Telegram Bot Manager
Простой и красивый бот для управления n8n workflows

Для запуска:
1. Скопируйте .env.example в .env
2. Заполните настройки в .env файле
3. Запустите: python start_bot.py
"""

import os
import sys
import logging
from pathlib import Path

def check_requirements():
    """Проверка установки зависимостей"""
    required_packages = [
        'python-telegram-bot',
        'requests', 
        'aiohttp',
        'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Отсутствуют необходимые пакеты:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Установите зависимости:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Проверка конфигурации"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("\n📝 Создайте файл .env:")
        print("   1. Скопируйте .env.example в .env")
        print("   2. Заполните настройки в .env файле")
        
        if os.path.exists('.env.example'):
            print("\n💡 Пример конфигурации в .env.example")
        
        return False
    
    # Загружаем переменные окружения
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'N8N_API_KEY': 'n8n API Key', 
        'ALLOWED_USERS': 'Список разрешенных пользователей'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        print("❌ Отсутствуют обязательные настройки в .env:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Заполните недостающие настройки в .env файле")
        return False
    
    return True

def print_startup_info():
    """Информация о запуске"""
    print("🤖 n8n Telegram Bot Manager")
    print("=" * 40)
    print("🚀 Запуск бота...")
    
    # Показываем основную информацию
    from dotenv import load_dotenv
    load_dotenv()
    
    n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
    allowed_users = os.getenv('ALLOWED_USERS', '')
    user_count = len([u for u in allowed_users.split(',') if u.strip()])
    
    print(f"🔗 n8n URL: {n8n_url}")
    print(f"👥 Разрешенных пользователей: {user_count}")
    print("=" * 40)

def main():
    """Главная функция запуска"""
    print("🔍 Проверка системы...")
    
    # Проверяем зависимости
    if not check_requirements():
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    # Показываем информацию о запуске
    print_startup_info()
    
    # Запускаем бота
    try:
        from main import N8NTelegramBot
        bot = N8NTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        print("\n💡 Проверьте:")
        print("1. Правильность настроек в .env")
        print("2. Доступность n8n сервера")
        print("3. Корректность API ключей")
        sys.exit(1)

if __name__ == "__main__":
    main()
