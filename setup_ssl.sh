#!/bin/bash
# Установка SSL сертификата Let's Encrypt
# Запускать на сервере

set -e

echo "🔒 Установка SSL сертификата..."

# Установка Certbot
if ! command -v certbot &> /dev/null; then
    echo "📦 Установка Certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    echo "✓ Certbot установлен"
fi

# Получение сертификата
echo "🔐 Получение SSL сертификата для profsouz.com и www.profsouz.com..."
certbot --nginx -d profsouz.com -d www.profsouz.com --non-interactive --agree-tos --email admin@profsouz.com --redirect

echo "✅ SSL сертификат установлен!"

# Настройка автообновления
echo "🔄 Настройка автообновления сертификата..."
systemctl enable certbot.timer
systemctl start certbot.timer

echo "✅ Автообновление настроено!"

# Проверка срока действия
certbot certificates

echo "✅ Готово! Ваш сайт теперь работает по HTTPS"

