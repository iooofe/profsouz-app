#!/bin/bash
# Скрипт первоначальной настройки сервера для Django приложения
# Запускать на сервере с правами root

set -e

echo "🔧 Начинаю настройку сервера..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Обновление системы
echo -e "${YELLOW}📦 Обновление системы...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${GREEN}✓ Система обновлена${NC}"

# Установка необходимых пакетов
echo -e "${YELLOW}📦 Установка пакетов...${NC}"
apt-get install -y python3.12 python3.12-venv python3-pip git nginx supervisor

echo -e "${GREEN}✓ Пакеты установлены${NC}"

# Создание пользователя для приложения (если не существует)
if ! id "profsouz" &>/dev/null; then
    echo -e "${YELLOW}👤 Создание пользователя profsouz...${NC}"
    adduser --disabled-password --gecos "" profsouz
    echo -e "${GREEN}✓ Пользователь создан${NC}"
else
    echo -e "${GREEN}✓ Пользователь profsouz уже существует${NC}"
fi

# Создание директорий
echo -e "${YELLOW}📁 Создание директорий...${NC}"
mkdir -p /home/profsouz/profsouz
mkdir -p /home/profsouz/logs
chown -R profsouz:profsouz /home/profsouz

echo -e "${GREEN}✓ Директории созданы${NC}"

# Клонирование репозитория (если еще не клонирован)
if [ ! -d "/home/profsouz/profsouz/.git" ]; then
    echo -e "${YELLOW}📥 Клонирование репозитория...${NC}"
    cd /home/profsouz
    sudo -u profsouz git clone https://github.com/iooofe/profsouz-app.git profsouz
    echo -e "${GREEN}✓ Репозиторий клонирован${NC}"
else
    echo -e "${GREEN}✓ Репозиторий уже существует${NC}"
fi

# Создание виртуального окружения
if [ ! -d "/home/profsouz/venv" ]; then
    echo -e "${YELLOW}🐍 Создание виртуального окружения...${NC}"
    sudo -u profsouz python3.12 -m venv /home/profsouz/venv
    echo -e "${GREEN}✓ Виртуальное окружение создано${NC}"
else
    echo -e "${GREEN}✓ Виртуальное окружение уже существует${NC}"
fi

# Активация venv и установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
sudo -u profsouz /home/profsouz/venv/bin/pip install --upgrade pip
sudo -u profsouz /home/profsouz/venv/bin/pip install -r /home/profsouz/profsouz/requirements.txt

echo -e "${GREEN}✓ Зависимости установлены${NC}"

# Установка Gunicorn
echo -e "${YELLOW}🔧 Установка Gunicorn...${NC}"
sudo -u profsouz /home/profsouz/venv/bin/pip install gunicorn

echo -e "${GREEN}✓ Gunicorn установлен${NC}"

echo -e "${GREEN}✅ Базовая настройка сервера завершена!${NC}"
echo -e "${YELLOW}⚠️  Следующие шаги:${NC}"
echo "1. Настройте переменные окружения в /home/profsouz/profsouz/.env"
echo "2. Примените миграции: sudo -u profsouz /home/profsouz/venv/bin/python /home/profsouz/profsouz/manage.py migrate"
echo "3. Создайте пользователей: sudo -u profsouz /home/profsouz/venv/bin/python /home/profsouz/profsouz/manage.py create_users"
echo "4. Соберите статику: sudo -u profsouz /home/profsouz/venv/bin/python /home/profsouz/profsouz/manage.py collectstatic --noinput"
echo "5. Настройте systemd service (см. profsouz.service)"
echo "6. Настройте Nginx (см. nginx_profsouz.conf)"
echo "7. Установите SSL сертификат (см. setup_ssl.sh)"

