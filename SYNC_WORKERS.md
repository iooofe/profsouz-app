# Автоматическая синхронизация работников

## Локальный запуск

Для создания пользователей и импорта работников из Excel файлов локально:

```bash
cd /Users/iofe/Desktop/profsouz
source venv/bin/activate
python manage.py create_users
```

Эта команда:
- Найдет все `.xlsx` файлы в папке `работники`
- Создаст пользователей по именам файлов (без расширения)
- Импортирует всех работников из каждого файла в соответствующий аккаунт

## Автоматический запуск на сервере

### Вариант 1: При деплое (уже настроено)

Команда `create_users` автоматически запускается при каждом деплое через `deploy_full.sh`:

```bash
# На сервере
bash deploy_full.sh
```

### Вариант 2: При старте системы (systemd service)

Для автоматического запуска при старте сервера:

1. Скопируйте service файл:
```bash
sudo cp profsouz-sync-workers.service /etc/systemd/system/
```

2. Отредактируйте пути в файле (если нужно):
```bash
sudo nano /etc/systemd/system/profsouz-sync-workers.service
```

3. Перезагрузите systemd и включите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable profsouz-sync-workers.service
```

4. Запустите вручную для проверки:
```bash
sudo systemctl start profsouz-sync-workers.service
sudo systemctl status profsouz-sync-workers.service
```

5. Просмотр логов:
```bash
sudo journalctl -u profsouz-sync-workers.service -f
```

### Вариант 3: Периодическая синхронизация (cron)

Для периодической синхронизации (например, каждый день в 3:00):

1. Откройте crontab:
```bash
sudo crontab -e
```

2. Добавьте строку:
```bash
0 3 * * * cd /var/www/profsouz && /var/www/profsouz/venv/bin/python manage.py create_users >> /var/log/profsouz-sync.log 2>&1
```

### Вариант 4: Ручной запуск на сервере

```bash
cd /var/www/profsouz
source venv/bin/activate
python manage.py create_users
```

## Структура Excel файлов

- Название файла (без `.xlsx`) = имя пользователя/аккаунта
- Файл должен содержать таблицу с работниками
- Обязательные столбцы: табельный номер, ФИО
- Поддерживаемые столбцы: ИНН, участок, должность, статус, дата вступления, адрес, телефон

## Логи и отладка

При запуске команда выводит:
- ✓ Создан пользователь: [имя]
- ✓ Создан работник: [ФИО] ([табельный номер])
- ↻ Обновлен работник: [ФИО] ([табельный номер])

Ошибки отображаются в консоли или в логах systemd/cron.

