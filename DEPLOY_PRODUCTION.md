# Инструкция по развертыванию проекта в продакшене

## Быстрый старт (автоматический деплой)

### Вариант 1: Полный автоматический деплой с нуля

```bash
# Подключитесь к серверу
ssh root@your-server-ip
# Пароль: ваш_пароль

# Выполните команду для автоматического развертывания
cd /root
bash <(curl -s https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh)
```

Скрипт автоматически:
- Установит все необходимые пакеты
- Склонирует репозиторий из GitHub
- Настроит виртуальное окружение
- Установит зависимости
- Применит миграции
- Создаст пользователей
- **Импортирует работников из файлов в папке `работники`**
- Настроит Nginx и Gunicorn
- Получит SSL сертификат (если домен настроен)

### Вариант 2: Обновление существующего проекта

```bash
# На сервере
cd /var/www/profsouz
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
supervisorctl restart profsouz
```

## Импорт работников

После деплоя работники автоматически импортируются из файлов в папке `работники`.

Если нужно импортировать вручную или обновить данные:

```bash
cd /var/www/profsouz
source venv/bin/activate
python manage.py import_workers_from_files
```

## Структура файлов работников

Файлы должны быть в папке `работники` в корне проекта:
- Формат: `.docx`
- Структура: таблица с колонками: №, таб.№, фамилия, имя, отчество, должность, дата вступления
- Названия файлов должны соответствовать пользователям в системе (см. `FILE_USER_MAP` в команде импорта)

## Проверка после деплоя

1. Проверьте статус сервисов:
```bash
systemctl status nginx
supervisorctl status profsouz
```

2. Проверьте логи:
```bash
# Логи Gunicorn
tail -f /var/log/gunicorn/profsouz_error.log

# Логи Nginx
tail -f /var/log/nginx/profsouz_error.log
```

3. Откройте сайт в браузере:
- HTTP: http://profsouz.kz
- HTTPS: https://profsouz.kz (после получения SSL)

4. Войдите в систему:
- Логин: `АДМИН`
- Пароль: `change-me`

## Управление проектом

### Перезапуск приложения
```bash
supervisorctl restart profsouz
```

### Обновление кода
```bash
cd /var/www/profsouz
source venv/bin/activate
git pull
pip install -r requirements.txt  # если изменились зависимости
python manage.py migrate  # если есть новые миграции
python manage.py collectstatic --noinput
supervisorctl restart profsouz
```

### Резервное копирование
```bash
# База данных
cd /var/www/profsouz
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)

# Медиа файлы
tar -czf /root/media_backup_$(date +%Y%m%d).tar.gz /var/www/profsouz/media/
```

## Решение проблем

### Приложение не запускается
```bash
supervisorctl tail profsouz stderr
# Проверьте ошибки в логах
```

### Nginx возвращает 502
```bash
# Проверьте статус Gunicorn
supervisorctl status profsouz

# Перезапустите
supervisorctl restart profsouz
```

### Статические файлы не загружаются
```bash
cd /var/www/profsouz
source venv/bin/activate
python manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/profsouz/staticfiles
```

## Безопасность

- ✅ SSL сертификат настроен автоматически
- ✅ Firewall настроен (порты 22, 80, 443)
- ✅ Секретные ключи в `.env` (не в Git)
- ✅ Регулярные обновления системы

## Контакты

При возникновении проблем проверьте логи и следуйте инструкциям выше.

