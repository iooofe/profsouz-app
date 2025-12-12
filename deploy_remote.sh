#!/bin/bash
# Скрипт для удаленного развертывания
# Использование с локального компьютера

SERVER="root@your-server-ip"
DEPLOY_SCRIPT="https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh"

echo "🚀 Начало удаленного развертывания..."

# Подключение к серверу и выполнение скрипта
ssh -o StrictHostKeyChecking=no $SERVER << 'REMOTE_SCRIPT'
    cd /root
    wget -q https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh -O deploy_full.sh
    chmod +x deploy_full.sh
    bash deploy_full.sh
REMOTE_SCRIPT

echo "✅ Развертывание завершено!"
