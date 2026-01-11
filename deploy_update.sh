#!/bin/bash
# Быстрое обновление на сервере одной командой
# Использование: ./deploy_update.sh

echo "🚀 Обновление проекта на сервере..."
echo ""
echo "Выполните на сервере следующие команды:"
echo ""
echo "ssh root@your-server-ip"
echo "cd /var/www/profsouz"
echo "source venv/bin/activate"
echo "git pull"
echo "pip install -r requirements.txt"
echo "mkdir -p backups && cp db.sqlite3 backups/db_backup_\$(date +%Y%m%d_%H%M%S).sqlite3"
echo "python manage.py migrate"
echo "python manage.py collectstatic --noinput"
echo "supervisorctl restart profsouz"
echo "supervisorctl status profsouz"
echo ""
echo "Или просто запустите:"
echo "bash update_on_server.sh"
echo ""

