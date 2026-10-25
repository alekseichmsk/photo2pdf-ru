FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng espeak-ng curl fonts-dejavu-core libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
# Render sets PORT (default 10000); app binds 0.0.0.0:$PORT
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PORT=10000 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OMP_THREAD_LIMIT=1
WORKDIR /home/user/app
# argostranslate only to download the en->ru model at build time; runtime uses ctranslate2+sentencepiece directly (low RAM)
RUN pip install --no-cache-dir --user argostranslate==1.11.0 weasyprint==70.0
COPY --chown=user . .
RUN mkdir -p data && curl -fsSL -o data/en_UK.txt https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_UK.txt && \
    python -c "import argostranslate.package as p;p.update_package_index();p.install_from_path([x for x in p.get_available_packages() if x.from_code=='en' and x.to_code=='ru'][0].download())" && \
    rm -rf /home/user/.local/share/argos-translate/packages/*/stanza
EXPOSE 10000
CMD ["python","app.py"]
