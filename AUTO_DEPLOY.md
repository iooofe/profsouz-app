# Автоматическое развертывание проекта

## Быстрый старт

### Вариант 1: Клонирование репозитория (Рекомендуется)

Самый простой способ - скрипт сам клонирует репозиторий:

```bash
# Подключитесь к серверу
ssh root@your-server-ip
# Пароль: ваш_пароль

# Клонируйте репозиторий и запустите скрипт
cd /root
git clone https://github.com/iooofe/profsouz-app.git temp_repo
cp temp_repo/deploy_full.sh .
rm -rf temp_repo
chmod +x deploy_full.sh
./deploy_full.sh
```

### Вариант 2: Загрузка файлов через scp

Если предпочитаете загрузить файлы вручную:

```bash
# С вашего локального компьютера
cd /Users/iofe/Desktop/profsouz
scp deploy_full.sh nginx_profsouz.conf gunicorn_profsouz.conf root@your-server-ip:/root/

# На сервере
ssh root@your-server-ip
chmod +x /root/deploy_full.sh
/root/deploy_full.sh
```

## Что делает скрипт

Скрипт автоматически выполнит:
- ✅ Установку всех необходимых пакетов (Python 3.12, Nginx, Supervisor, Certbot и др.)
- ✅ Клонирование репозитория из GitHub
- ✅ Создание виртуального окружения Python
- ✅ Установку зависимостей из requirements.txt
- ✅ Генерацию SECRET_KEY и создание .env файла
- ✅ Применение миграций базы данных
- ✅ Создание пользователей системы
- ✅ Импорт работников из файлов в папке `работники` (если папка существует)
- ✅ Сбор статических файлов
- ✅ Настройку Nginx (HTTP, без SSL)
- ✅ Настройку Gunicorn через Supervisor
- ✅ Попытку получения SSL сертификата (если домен настроен)

## После выполнения скрипта

### Проверка работы сервисов

После выполнения скрипта проверьте статус:

```bash
systemctl status nginx
supervisorctl status profsouz
```

Если Nginx не запустился, проверьте конфигурацию:
```bash
nginx -t
```

### Получение SSL сертификата

Если домен `profsouz.kz` уже указывает на сервер `your-server-ip`, скрипт попытается получить SSL сертификат автоматически.

Если сертификат не был получен автоматически, выполните вручную:

```bash
certbot --nginx -d profsouz.kz -d www.profsouz.kz --non-interactive --agree-tos --email admin@profsouz.kz
```

Certbot автоматически обновит конфигурацию Nginx и добавит HTTPS.

### Проверка работы сайта

- Откройте в браузере: **http://profsouz.kz** (или **https://** после получения сертификата)
- Вход в систему: 
  - Логин: `АДМИН`
  - Пароль: `change-me`

## Проверка логов при ошибках

```bash
# Логи Gunicorn
tail -f /var/log/gunicorn/profsouz_error.log

# Логи Nginx
tail -f /var/log/nginx/profsouz_error.log

# Логи Supervisor
supervisorctl tail -f profsouz stdout
```

