#!/bin/bash
# Скрипт для подготовки и загрузки изменений на GitHub

set -e

echo "🚀 Подготовка проекта к продакшену..."

# Проверка что мы в git репозитории
if [ ! -d ".git" ]; then
    echo "❌ Это не git репозиторий. Инициализируйте репозиторий:"
    echo "   git init"
    echo "   git remote add origin https://github.com/iooofe/profsouz-app.git"
    exit 1
fi

# Проверка что нет незакоммиченных секретов
echo "🔍 Проверка на наличие секретов..."
if grep -r "github_pat_" --exclude-dir=venv --exclude="*.pyc" . 2>/dev/null | grep -v "COMMIT_AND_PUSH.sh" | grep -v "PREPARE_PRODUCTION.md"; then
    echo "⚠️  ВНИМАНИЕ: Найдены возможные токены в файлах!"
    echo "   Проверьте файлы перед коммитом"
    read -p "Продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Добавление всех изменений
echo "📦 Добавление изменений..."
git add -A

# Показ статуса
echo ""
echo "📊 Статус изменений:"
git status --short

# Запрос подтверждения
echo ""
read -p "Создать коммит и отправить на GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Отменено"
    exit 0
fi

# Создание коммита
echo "💾 Создание коммита..."
git commit -m "feat: переработана команда create_users для работы с Excel файлами

- Команда теперь читает Excel файлы из папки 'работники'
- Название файла = имя пользователя/аккаунта
- Автоматический импорт всех работников из каждого файла
- Улучшена обработка табельных номеров (сохранение полной точности)
- Добавлена автоматическая синхронизация при деплое
- Убраны токены из скриптов деплоя (используются переменные окружения)
- Исправлена обработка файлов с разными структурами заголовков"

# Определение ветки
BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ]; then
    BRANCH="main"
fi

echo "📤 Отправка на GitHub (ветка: $BRANCH)..."
git push origin $BRANCH

echo ""
echo "✅ Готово! Изменения отправлены на GitHub"
echo ""
echo "Следующие шаги:"
echo "1. На сервере обновите код: git pull"
echo "2. Запустите миграции: python manage.py migrate"
echo "3. Запустите создание пользователей: python manage.py create_users"
echo "4. Перезапустите сервисы: supervisorctl restart profsouz"

