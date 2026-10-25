#!/bin/sh
# Скачивает британский словарь транскрипций (ipa-dict, en_UK, на основе Викисловаря) и модель перевода en->ru
set -e
cd "$(dirname "$0")"; mkdir -p data
curl -fsSL -o data/en_UK.txt https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_UK.txt
venv/bin/python -c "import argostranslate.package as p;p.update_package_index();p.install_from_path([x for x in p.get_available_packages() if x.from_code=='en' and x.to_code=='ru'][0].download())"
