@echo off
echo Запуск обработки данных EORA Knowledge Base...

echo Этап 1/4: Загрузка HTML-страниц
python src\ingestion\fetcher.py

echo Этап 2/4: Парсинг HTML в чистый текст
python src\ingestion\parser.py

echo Этап 3/4: Разбиение текста на чанки
python src\ingestion\chunker.py

echo Этап 4/4: Построение векторного индекса
python -m src.embeddings.indexer

echo Обработка данных завершена!
pause