#!/usr/bin/env python3
"""
🚀 Быстрый запуск n8n Telegram Bot

Использование:
1. Создайте файл .env (скопируйте из .env.example)
2. Заполните настройки
3. Запустите: python quick_start.py
"""

import os
import sys

def create_env_file():
    """Создание файла .env из примера"""
    if not os.path.exists('.env') and os.path.exists('.env.example'):
        print("📝 Создаю .env файл из примера...")
        with open('.env.example', 'r') as example:
            content = example.read()
        with open('.env', 'w') as env_file:
            env_file.write(content)
        print("✅ Файл .env создан!")
        return True
    return False

def check_and_install_requirements():
    """Проверка и установка зависимостей"""
    try:
        import telegram
        import aiohttp
        import requests
        from dotenv import load_dotenv
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует пакет: {e.name}")
        print("📦 Устанавливаю зависимости...")
        
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Зависимости установлены успешно!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Ошибка установки зависимостей")
            print("💡 Попробуйте вручную: pip install -r requirements.txt")
            return False

def main():
    """Главная функция"""
    print("🤖 n8n Telegram Bot - Быстрый запуск")
    print("=" * 50)
    
    # Создаем .env файл если нужно
    if create_env_file():
        print("\n⚠️  ВАЖНО: Отредактируйте .env файл!")
        print("   1. Добавьте TELEGRAM_BOT_TOKEN")
        print("   2. Добавьте N8N_API_KEY") 
        print("   3. Добавьте ALLOWED_USERS")
        print("   4. Проверьте N8N_BASE_URL")
        print("\n📝 Откройте .env файл в редакторе и заполните настройки")
        input("\n⏸️  Нажмите Enter после настройки .env файла...")
    
    # Проверяем зависимости
    if not check_and_install_requirements():
        return
    
    # Проверяем конфигурацию
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Создайте .env файл и заполните настройки")
        return
    
    # Запускаем простую версию бота
    print("\n🚀 Запускаю бота...")
    try:
        import simple_bot
        bot = simple_bot.SimpleN8NBot()
        print("✅ Бот запущен успешно!")
        print("📱 Попробуйте написать боту /start")
        print("⏹️  Для остановки нажмите Ctrl+C")
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Проверьте настройки в .env файле:")
        print("   - TELEGRAM_BOT_TOKEN должен быть корректным")
        print("   - N8N_API_KEY должен быть корректным")
        print("   - ALLOWED_USERS должен содержать ваш Telegram ID")
        print("   - N8N_BASE_URL должен быть доступным")

if __name__ == "__main__":
    main()
