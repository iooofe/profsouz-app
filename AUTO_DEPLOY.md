# Автоматическое развертывание проекта

## Вариант 1: Выполнение на сервере (Рекомендуется)

Подключитесь к серверу и выполните **ОДНУ** команду:

```bash
ssh root@your-server-ip
# Введите пароль: ваш_пароль

# Затем выполните эту команду:
bash <(curl -s https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh)
```

Эта команда автоматически:
- Установит все необходимые пакеты
- Клонирует репозиторий
- Настроит Python окружение
- Установит зависимости
- Настроит Nginx
- Настроит Gunicorn через Supervisor
- Попытается получить SSL сертификат

## Вариант 2: Пошаговое выполнение

Если автоматический скрипт не работает, выполните пошагово:

```bash
ssh root@your-server-ip
# Пароль: ваш_пароль

cd /root
wget https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh
chmod +x deploy_full.sh
./deploy_full.sh
```

## После выполнения скрипта

1. Проверьте статус сервисов:
```bash
systemctl status nginx
supervisorctl status profsouz
```

2. Если SSL сертификат не получен автоматически:
```bash
certbot --nginx -d profsouz.com -d www.profsouz.com
```

3. Проверьте работу сайта:
- Откройте в браузере: http://profsouz.com (или https:// после получения сертификата)
- Попробуйте войти: Логин `АДМИН`, Пароль `change-me`

## Проверка логов при ошибках

```bash
# Логи Gunicorn
tail -f /var/log/gunicorn/profsouz_error.log

# Логи Nginx
tail -f /var/log/nginx/profsouz_error.log

# Логи Supervisor
supervisorctl tail -f profsouz stdout
```

