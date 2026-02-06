# Инструкция по деплою проекта на сервер

## ✅ Проект готов к продакшену!

Все изменения залиты в Git репозиторий: `https://github.com/iooofe/profsouz-app.git`

## 🚀 Быстрый деплой на сервер

### Автоматический деплой с нуля

Подключитесь к серверу и выполните одну команду:

```bash
ssh root@your-server-ip
# Пароль: (укажите свой пароль / используйте SSH-ключ)

# Выполните автоматический деплой
bash <(curl -s https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh)
```

Скрипт автоматически:
1. ✅ Установит все необходимые пакеты
2. ✅ Склонирует репозиторий из GitHub
3. ✅ Настроит виртуальное окружение
4. ✅ Установит зависимости
5. ✅ Применит миграции
6. ✅ Создаст пользователей системы
7. ✅ **Импортирует работников из файлов в папке `работники`**
8. ✅ Настроит Nginx и Gunicorn
9. ✅ Получит SSL сертификат

## 📋 Что включено в деплой

### Автоматический импорт работников

При деплое автоматически выполняется команда:
```bash
python manage.py import_workers_from_files
```

Она обрабатывает все `.docx` файлы в папке `работники` и создает карточки работников для каждого предприятия.

### Структура файлов работников

Файлы должны быть в папке `работники` в корне проекта:
- Формат: `.docx` (Word документы с таблицами)
- Структура: таблица с колонками: №, таб.№, фамилия, имя, отчество, должность, дата вступления
- Названия файлов должны соответствовать пользователям (см. `FILE_USER_MAP` в команде импорта)

## 🔄 Обновление существующего проекта

Если проект уже развернут, для обновления:

```bash
cd /var/www/profsouz
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py import_workers_from_files  # Обновить работников
supervisorctl restart profsouz
```

## 📝 Проверка после деплоя

1. **Проверьте статус сервисов:**
```bash
systemctl status nginx
supervisorctl status profsouz
```

2. **Проверьте логи:**
```bash
tail -f /var/log/gunicorn/profsouz_error.log
tail -f /var/log/nginx/profsouz_error.log
```

3. **Откройте сайт:**
- HTTP: http://profsouz.kz
- HTTPS: https://profsouz.kz

4. **Войдите в систему:**
- Логин: `АДМИН`
- Пароль: (см. команду `python manage.py create_users` / задайте свой)

## 🛠️ Управление проектом

### Перезапуск приложения
```bash
supervisorctl restart profsouz
```

### Просмотр логов
```bash
# Логи Gunicorn
tail -f /var/log/gunicorn/profsouz_error.log

# Логи Nginx
tail -f /var/log/nginx/profsouz_error.log

# Логи Supervisor
supervisorctl tail -f profsouz stdout
```

### Резервное копирование
```bash
# База данных
cd /var/www/profsouz
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)

# Медиа файлы
tar -czf /root/media_backup_$(date +%Y%m%d).tar.gz /var/www/profsouz/media/
```

## 📚 Дополнительная документация

- `AUTO_DEPLOY.md` - Автоматическое развертывание
- `DEPLOYMENT.md` - Подробная инструкция по развертыванию
- `DEPLOY_PRODUCTION.md` - Руководство по продакшену
- `PRODUCTION_README.md` - Настройки для продакшена

## 🔐 Безопасность

- ✅ SSL сертификат настроен автоматически
- ✅ Firewall настроен (порты 22, 80, 443)
- ✅ Секретные ключи в `.env` (не в Git)
- ✅ Регулярные обновления системы

## ⚠️ Важные замечания

1. **Папка `работники`** должна быть в репозитории для автоматического импорта
2. **Временные файлы Word** (`~$*.docx`) автоматически игнорируются
3. **База данных** (`db.sqlite3`) не попадает в Git (в `.gitignore`)
4. **Медиа файлы** не попадают в Git (в `.gitignore`)

## 🆘 Решение проблем

Если что-то пошло не так, проверьте:
1. Логи сервисов (см. выше)
2. Права доступа: `chown -R www-data:www-data /var/www/profsouz`
3. Статус сервисов: `systemctl status nginx` и `supervisorctl status profsouz`

