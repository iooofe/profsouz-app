# Инструкция по обновлению проекта на сервере

## 🚀 Быстрое обновление

### Шаг 1: Подключитесь к серверу
```bash
ssh root@your-server-ip
# Пароль: (укажите свой пароль / используйте SSH-ключ)
```

### Шаг 2: Запустите скрипт обновления
```bash
cd /var/www/profsouz
bash update_on_server.sh
```

Скрипт автоматически выполнит:
- ✅ Обновление кода из Git (`git pull`)
- ✅ Обновление зависимостей (`pip install -r requirements.txt`)
- ✅ Создание резервной копии базы данных
- ✅ Применение миграций (`python manage.py migrate`)
- ✅ Сбор статических файлов (`python manage.py collectstatic`)
- ✅ Перезапуск приложения (`supervisorctl restart profsouz`)

## 📋 Ручное обновление (если нужно)

Если хотите выполнить команды вручную:

```bash
cd /var/www/profsouz
source venv/bin/activate

# Обновление кода
git pull

# Обновление зависимостей
pip install -r requirements.txt

# Резервная копия базы данных
mkdir -p backups
cp db.sqlite3 backups/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3

# Применение миграций (важно! у нас новая миграция 0020_vacationrequest_seasons.py)
python manage.py migrate

# Сбор статических файлов
python manage.py collectstatic --noinput

# Перезапуск приложения
supervisorctl restart profsouz

# Проверка статуса
supervisorctl status profsouz
```

## ✅ Проверка после обновления

1. **Проверьте статус сервисов:**
```bash
supervisorctl status profsouz
systemctl status nginx
```

2. **Проверьте логи (если нужно):**
```bash
tail -f /var/log/gunicorn/profsouz_error.log
```

3. **Откройте сайт в браузере:**
- https://profsouz.com (или другой домен)

## 📝 Что было обновлено

- ✅ Добавлены сезоны для отпусков (миграция `0020_vacationrequest_seasons.py`)
- ✅ Обновлены модели и представления
- ✅ Улучшения UI (CSS и шаблоны)
- ✅ Новый скрипт обновления `deploy_update.sh`

## ⚠️ Важно

- Миграция `0020_vacationrequest_seasons.py` будет применена автоматически
- Резервная копия базы данных создается автоматически
- Приложение перезапускается автоматически после обновления

