#!/bin/bash
# Полный скрипт настройки сервера с нуля
# Запускать на сервере от root

set -e

echo "🚀 Начало настройки сервера для проекта Профоюз..."

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
echo "📦 Установка базовых пакетов..."
apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor \
    sqlite3 \
    curl \
    wget \
    ufw

# Настройка firewall
echo "🔥 Настройка firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Создание директории проекта
PROJECT_DIR="/var/www/profsouz"
echo "📁 Создание директории проекта: $PROJECT_DIR..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Клонирование репозитория
echo "📥 Клонирование репозитория..."
# GitHub token должен быть установлен как переменная окружения
# export GITHUB_TOKEN="your_token_here"
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN не установлен, клонирую без токена..."
    git clone "https://github.com/iooofe/profsouz-app.git" .
else
    git clone "https://${GITHUB_TOKEN}@github.com/iooofe/profsouz-app.git" .
fi

# Создание виртуального окружения
VENV_DIR="$PROJECT_DIR/venv"
echo "🐍 Создание виртуального окружения..."
python3.12 -m venv $VENV_DIR

# Активация и установка зависимостей
echo "📦 Установка зависимостей Python..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Генерация SECRET_KEY
echo "🔑 Генерация SECRET_KEY..."
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Создание файла .env
echo "⚙️  Создание файла .env..."
cat > $PROJECT_DIR/.env << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=profsouz.com,www.profsouz.com
SECURE_SSL_REDIRECT=True
EOF

# Применение миграций
echo "🗄️  Применение миграций базы данных..."
python manage.py migrate

# Создание пользователей
echo "👤 Создание пользователей системы (опционально)..."
if [ "${PROFSOUZ_RUN_CREATE_USERS:-0}" = "1" ]; then
    echo "⚠️  PROFSOUZ_RUN_CREATE_USERS=1 — запускаю create_users (может импортировать работников из Excel)"
    python manage.py create_users
else
    echo "⏭️  Пропускаю create_users. (Чтобы запустить: export PROFSOUZ_RUN_CREATE_USERS=1)"
fi

# Сбор статических файлов
echo "📦 Сбор статических файлов..."
python manage.py collectstatic --noinput

# Установка прав доступа
echo "🔐 Настройка прав доступа..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles

# Создание директорий для media
mkdir -p $PROJECT_DIR/media/{benefits,miner_glory,coal,funeral}
chown -R www-data:www-data $PROJECT_DIR/media

echo "✅ Базовая настройка завершена!"
echo ""
echo "📝 Сгенерированный SECRET_KEY сохранен в .env файл"
echo ""
echo "⚠️  Следующие шаги выполняются вручную:"
echo "1. Настройте Nginx (файл: /etc/nginx/sites-available/profsouz)"
echo "2. Настройте Gunicorn (файл: /etc/supervisor/conf.d/profsouz.conf)"
echo "3. Получите SSL сертификат: certbot --nginx -d profsouz.com -d www.profsouz.com"
echo "4. Запустите сервисы: systemctl restart nginx && supervisorctl reread && supervisorctl update"

