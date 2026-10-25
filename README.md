# Текст → PDF с транскрипцией

Офлайн-сайт: загружаете фото страницы учебника или вставляете английский текст и получаете PDF.
Над каждым словом стоит транскрипция русскими буквами (британское произношение), под строкой перевод.

Как это работает: Tesseract распознаёт текст с фото, словарь ipa-dict en_UK (данные Викисловаря) даёт транскрипцию,
для незнакомых слов используется eSpeak-NG, Argos Translate переводит на русский, WeasyPrint сохраняет PDF.

## Установка

    sudo apt install tesseract-ocr espeak-ng libpango-1.0-0 libpangoft2-1.0-0 && pip install weasyprint
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    ./get_dict.sh        # словарь и модель перевода, нужен интернет один раз

## Запуск

    venv/bin/python app.py      # откройте http://localhost:8080

## Тесты

    venv/bin/python -m pytest -q tests

Защита от спама: скрытое поле-ловушка, подписанная метка времени формы (не быстрее 3 секунд),
не более 10 запросов за 10 минут с одного IP (дальше нужен пример на сложение), фото до 10 МБ, текст до 5000 символов.

## Деплой на Render (бесплатно)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/alekseichmsk/photo2pdf-ru)

Docker-образ слушает `0.0.0.0:$PORT` (Render задаёт PORT, по умолчанию 10000). `render.yaml` создаёт бесплатный web-сервис и генерирует `APP_SECRET`.
