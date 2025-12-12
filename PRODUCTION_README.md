# Руководство по развертыванию в продакшене

## Подготовка к продакшену

Проект уже подготовлен к продакшену. Все тестовые данные удалены.

## Настройка переменных окружения

1. Скопируйте файл `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` и укажите:
   - `SECRET_KEY` - сгенерируйте новый секретный ключ:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - `DEBUG=False` - отключите режим отладки
   - `ALLOWED_HOSTS` - укажите ваш домен или IP адрес
   - `SECURE_SSL_REDIRECT=True` - если используете HTTPS

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Применение миграций

```bash
python manage.py migrate
```

## Создание пользователей

```bash
python manage.py create_users
```

Это создаст всех необходимых пользователей системы с паролями.

## Сбор статических файлов

```bash
python manage.py collectstatic --noinput
```

## Запуск сервера

### Для разработки (не рекомендуется для продакшена):
```bash
python manage.py runserver
```

### Для продакшена рекомендуется использовать:
- **Gunicorn** с Nginx
- **uWSGI** с Nginx
- **Django на Apache** с mod_wsgi

Пример с Gunicorn:
```bash
pip install gunicorn
gunicorn profsouz.wsgi:application --bind 0.0.0.0:8000
```

## Настройка веб-сервера (Nginx)

Пример конфигурации Nginx:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /static/ {
        alias /path/to/profsouz/staticfiles/;
    }

    location /media/ {
        alias /path/to/profsouz/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Проверка безопасности

После настройки проверьте настройки безопасности:
```bash
python manage.py check --deploy
```

## Структура директорий

- `staticfiles/` - собранные статические файлы (создается после `collectstatic`)
- `media/` - загруженные пользователями файлы
- `.env` - переменные окружения (не коммитьте в git!)

## Пользователи системы

После выполнения `python manage.py create_users` будут созданы следующие пользователи:

- **АДМИН** - административный аккаунт (полный доступ)
- Остальные пользователи - обычные аккаунты с ограничениями

Пароли указаны в файле `main/management/commands/create_users.py`.

## Резервное копирование

Регулярно создавайте резервные копии:
- База данных (SQLite: `db.sqlite3`)
- Директория `media/` с загруженными файлами

## Обновление

При обновлении проекта:
1. Остановите сервер
2. Обновите код
3. Выполните миграции: `python manage.py migrate`
4. Соберите статические файлы: `python manage.py collectstatic --noinput`
5. Перезапустите сервер

## Мониторинг

Рекомендуется настроить:
- Логирование ошибок
- Мониторинг дискового пространства
- Резервное копирование базы данных

