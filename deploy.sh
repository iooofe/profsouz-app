#!/bin/bash
# Скрипт автоматического развертывания проекта на сервер
# Использование: ./deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начало развертывания проекта Профоюз..."

# Переменные
REPO_URL="https://github.com/iooofe/profsouz-app.git"
DOMAIN="profsouz.com"
WWW_DOMAIN="www.profsouz.com"
PROJECT_DIR="/var/www/profsouz"
VENV_DIR="$PROJECT_DIR/venv"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка базовых пакетов
echo "📦 Установка базовых пакетов..."
apt install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx supervisor

# Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Клонирование репозитория (с использованием токена)
echo "📥 Клонирование репозитория..."
if [ -d ".git" ]; then
    echo "Респозиторий уже существует, обновление..."
    git pull
else
    git clone "https://${GITHUB_TOKEN}@github.com/iooofe/profsouz-app.git" .
fi

# Создание виртуального окружения
echo "🐍 Создание виртуального окружения..."
if [ ! -d "$VENV_DIR" ]; then
    python3.12 -m venv $VENV_DIR
fi

# Активация виртуального окружения и установка зависимостей
echo "📦 Установка зависимостей..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Установка Gunicorn
pip install gunicorn

# Генерация SECRET_KEY
echo "🔑 Генерация SECRET_KEY..."
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "Сгенерированный SECRET_KEY: $SECRET_KEY"

# Создание файла .env
echo "⚙️  Создание файла .env..."
cat > $PROJECT_DIR/.env << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,$WWW_DOMAIN
SECURE_SSL_REDIRECT=True
EOF

# Применение миграций
echo "🗄️  Применение миграций..."
python manage.py migrate

# Создание пользователей
echo "👤 Создание пользователей..."
python manage.py create_users

# Сбор статических файлов
echo "📦 Сбор статических файлов..."
python manage.py collectstatic --noinput

# Установка прав доступа
echo "🔐 Настройка прав доступа..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles

echo "✅ Развертывание завершено!"
echo ""
echo "Следующие шаги:"
echo "1. Настройте Nginx (конфигурация будет создана)"
echo "2. Настройте Gunicorn (конфигурация будет создана)"
echo "3. Получите SSL сертификат: certbot --nginx -d $DOMAIN -d $WWW_DOMAIN"
echo "4. Перезапустите сервисы: systemctl restart nginx supervisor"
