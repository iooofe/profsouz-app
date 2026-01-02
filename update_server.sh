#!/bin/bash
# Скрипт для обновления кода на сервере
# Использование: ./update_server.sh

set -e  # Остановка при ошибке

echo "🚀 Начало обновления проекта на сервере..."

# Переменные
SERVER="root@your-server-ip"
PROJECT_DIR="/var/www/profsouz"

# Подключение к серверу и выполнение команд обновления
ssh -o StrictHostKeyChecking=no $SERVER << 'REMOTE_SCRIPT'
    set -e
    
    echo "📥 Обновление кода из Git..."
    cd /var/www/profsouz
    source venv/bin/activate
    
    echo "🔄 Получение последних изменений..."
    git pull
    
    echo "📦 Обновление зависимостей (если нужно)..."
    pip install -r requirements.txt --quiet
    
    echo "🗄️  Применение миграций..."
    python manage.py migrate
    
    echo "📦 Сбор статических файлов..."
    python manage.py collectstatic --noinput
    
    echo "🔄 Перезапуск приложения..."
    supervisorctl restart profsouz
    
    echo "✅ Обновление завершено!"
    echo ""
    echo "Проверка статуса:"
    supervisorctl status profsouz
REMOTE_SCRIPT

echo "✅ Обновление на сервере завершено!"

