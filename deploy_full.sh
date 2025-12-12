#!/bin/bash
# Полный скрипт автоматического развертывания с настройкой Nginx и Gunicorn
# Запускать на сервере от root одной командой

set -e

echo "🚀 Начало полного развертывания проекта Профоюз..."

# Переменные
PROJECT_DIR="/var/www/profsouz"
DOMAIN="profsouz.com"
WWW_DOMAIN="www.profsouz.com"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Шаг 1: Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Шаг 2: Установка пакетов
echo "📦 Установка необходимых пакетов..."
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

# Шаг 3: Настройка firewall
echo "🔥 Настройка firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Шаг 4: Создание директории и клонирование
echo "📁 Создание директории проекта..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

if [ -d ".git" ]; then
    echo "Обновление репозитория..."
    git pull
else
    echo "Клонирование репозитория..."
    git clone "https://${GITHUB_TOKEN}@github.com/iooofe/profsouz-app.git" .
fi

# Шаг 5: Создание виртуального окружения
VENV_DIR="$PROJECT_DIR/venv"
echo "🐍 Создание виртуального окружения..."
if [ ! -d "$VENV_DIR" ]; then
    python3.12 -m venv $VENV_DIR
fi

# Шаг 6: Установка зависимостей
echo "📦 Установка зависимостей Python..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Шаг 7: Генерация SECRET_KEY и создание .env
echo "🔑 Генерация SECRET_KEY..."
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

echo "⚙️  Создание файла .env..."
cat > $PROJECT_DIR/.env << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,$WWW_DOMAIN
SECURE_SSL_REDIRECT=True
EOF

# Шаг 8: Применение миграций
echo "🗄️  Применение миграций базы данных..."
python manage.py migrate

# Шаг 9: Создание пользователей
echo "👤 Создание пользователей системы..."
python manage.py create_users

# Шаг 10: Сбор статических файлов
echo "📦 Сбор статических файлов..."
python manage.py collectstatic --noinput

# Шаг 11: Установка прав доступа
echo "🔐 Настройка прав доступа..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/staticfiles

# Шаг 12: Настройка Nginx
echo "🌐 Настройка Nginx..."
cp $PROJECT_DIR/nginx_profsouz.conf /etc/nginx/sites-available/profsouz
ln -sf /etc/nginx/sites-available/profsouz /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации Nginx
nginx -t

# Шаг 13: Создание директории для логов Gunicorn
echo "📝 Создание директорий для логов..."
mkdir -p /var/log/gunicorn

# Шаг 14: Настройка Supervisor для Gunicorn
echo "⚙️  Настройка Supervisor..."
cp $PROJECT_DIR/gunicorn_profsouz.conf /etc/supervisor/conf.d/profsouz.conf

# Шаг 15: Запуск сервисов
echo "🚀 Запуск сервисов..."
systemctl restart nginx
supervisorctl reread
supervisorctl update
supervisorctl start profsouz || supervisorctl restart profsouz

# Шаг 16: Получение SSL сертификата
echo "🔒 Получение SSL сертификата..."
echo "⚠️  ВАЖНО: SSL сертификат будет запрошен автоматически"
echo "Если домен уже указывает на этот сервер, выполните:"
echo "certbot --nginx -d $DOMAIN -d $WWW_DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN"

# Попытка автоматического получения сертификата (может не сработать если домен еще не указывает на сервер)
certbot --nginx -d $DOMAIN -d $WWW_DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN 2>&1 || echo "⚠️  Не удалось получить сертификат автоматически. Убедитесь, что домен указывает на этот сервер."

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📊 Статус сервисов:"
systemctl status nginx --no-pager -l | head -5
echo ""
supervisorctl status profsouz
echo ""
echo "🌐 Проект доступен по адресу: http://$DOMAIN"
echo "🔒 После настройки SSL: https://$DOMAIN"

