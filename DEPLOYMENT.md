# Инструкция по развертыванию проекта на сервер

## Информация о сервере

- **IP:** your-server-ip
- **Домен:** profsouz.com, www.profsouz.com
- **ОС:** Ubuntu 24.04
- **Пользователь:** root

## Шаг 1: Подключение к серверу

```bash
ssh root@your-server-ip
# Пароль: (укажите свой пароль / используйте SSH-ключ)
```

## Шаг 2: Загрузка и выполнение скрипта настройки

```bash
# Скачайте скрипт на сервер
cd /root
wget https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_setup_server.sh

# Или загрузите файл вручную через scp с вашего компьютера:
# scp deploy_setup_server.sh root@your-server-ip:/root/

# Сделайте скрипт исполняемым
chmod +x deploy_setup_server.sh

# Запустите скрипт
./deploy_setup_server.sh
```

Скрипт автоматически:
- Обновит систему
- Установит Python 3.12, Nginx, Certbot, Supervisor
- Склонирует репозиторий
- Установит зависимости
- Создаст виртуальное окружение
- Сгенерирует SECRET_KEY
- Применит миграции
- Создаст пользователей
- Соберет статические файлы

## Шаг 3: Настройка Nginx

```bash
# Скопируйте конфигурацию Nginx
cp /var/www/profsouz/nginx_profsouz.conf /etc/nginx/sites-available/profsouz

# Создайте симлинк
ln -s /etc/nginx/sites-available/profsouz /etc/nginx/sites-enabled/

# Удалите дефолтную конфигурацию
rm /etc/nginx/sites-enabled/default

# Проверьте конфигурацию
nginx -t

# Перезапустите Nginx
systemctl restart nginx
```

## Шаг 4: Настройка Gunicorn (Supervisor)

```bash
# Создайте директорию для логов
mkdir -p /var/log/gunicorn

# Скопируйте конфигурацию Supervisor
cp /var/www/profsouz/gunicorn_profsouz.conf /etc/supervisor/conf.d/profsouz.conf

# Перезагрузите конфигурацию Supervisor
supervisorctl reread
supervisorctl update

# Запустите приложение
supervisorctl start profsouz

# Проверьте статус
supervisorctl status profsouz
```

## Шаг 5: Получение SSL сертификата

```bash
# Получите SSL сертификат от Let's Encrypt
certbot --nginx -d profsouz.com -d www.profsouz.com

# Следуйте инструкциям:
# - Введите email для уведомлений
# - Примите условия использования
# - Certbot автоматически настроит Nginx

# Проверьте автоматическое обновление сертификата
certbot renew --dry-run
```

После получения сертификата Certbot автоматически обновит конфигурацию Nginx с SSL настройками.

## Шаг 6: Проверка работы

1. Проверьте, что все сервисы работают:
```bash
systemctl status nginx
supervisorctl status profsouz
```

2. Откройте в браузере: https://profsouz.com

3. Попробуйте войти:
   - Логин: `АДМИН`
   - Пароль: (см. команду `python manage.py create_users` / задайте свой)

## Управление приложением

### Перезапуск приложения (после изменений в коде):
```bash
cd /var/www/profsouz
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
supervisorctl restart profsouz
```

### Просмотр логов:
```bash
# Логи Gunicorn
tail -f /var/log/gunicorn/profsouz_error.log
tail -f /var/log/gunicorn/profsouz_access.log

# Логи Nginx
tail -f /var/log/nginx/profsouz_error.log
tail -f /var/log/nginx/profsouz_access.log

# Логи Supervisor
supervisorctl tail -f profsouz stdout
```

### Обновление кода:
```bash
cd /var/www/profsouz
source venv/bin/activate
git pull
pip install -r requirements.txt  # если изменились зависимости
python manage.py migrate  # если есть новые миграции
python manage.py collectstatic --noinput  # если изменились статические файлы
supervisorctl restart profsouz
```

## Резервное копирование

### Создание резервной копии базы данных:
```bash
cd /var/www/profsouz
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
```

### Резервное копирование медиа файлов:
```bash
tar -czf media_backup_$(date +%Y%m%d).tar.gz /var/www/profsouz/media/
```

## Решение проблем

### Если приложение не запускается:
```bash
# Проверьте логи
supervisorctl tail profsouz

# Проверьте права доступа
ls -la /var/www/profsouz
chown -R www-data:www-data /var/www/profsouz
```

### Если Nginx возвращает 502 Bad Gateway:
```bash
# Проверьте, запущен ли Gunicorn
supervisorctl status profsouz

# Проверьте порт 8000
netstat -tlnp | grep 8000

# Перезапустите приложение
supervisorctl restart profsouz
```

### Если статические файлы не загружаются:
```bash
# Пересоберите статические файлы
cd /var/www/profsouz
source venv/bin/activate
python manage.py collectstatic --noinput

# Проверьте права
chown -R www-data:www-data /var/www/profsouz/staticfiles
```

## Безопасность

- Файл `.env` с секретными ключами НЕ должен попадать в Git
- Регулярно обновляйте систему: `apt update && apt upgrade`
- Настройте автоматическое обновление SSL сертификата
- Используйте firewall (уже настроен в скрипте)

## Контакты и поддержка

При возникновении проблем проверьте логи и следуйте инструкциям выше.
