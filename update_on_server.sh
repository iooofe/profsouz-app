#!/bin/bash
# Скрипт для обновления кода на сервере
# Запустить НА СЕРВЕРЕ: bash update_on_server.sh

set -e  # Остановка при ошибке

echo "🚀 Начало обновления проекта..."

cd /var/www/profsouz
source venv/bin/activate

echo "📥 Обновление кода из Git..."
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

