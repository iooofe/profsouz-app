#!/bin/bash
# Быстрый развертывание одной командой через curl
# Выполнить на сервере: bash <(curl -s https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh)

cd /root
wget -q https://raw.githubusercontent.com/iooofe/profsouz/main/deploy_full.sh -O deploy_full.sh
chmod +x deploy_full.sh
bash deploy_full.sh

