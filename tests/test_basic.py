import pytest
import tempfile
from pathlib import Path
from src.ingestion.parser import extract_text_from_html
from src.ingestion.chunker import chunk_text
from src.rag.response_formatter import add_html_links
import asyncio

def test_html_parsing():
    """Тест парсинга HTML."""
    test_html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <script>alert('test');</script>
            <div class="content">
                <h1>Заголовок</h1>
                <p>Основной текст с <a href="#">ссылкой</a>.</p>
            </div>
            <footer>Футер</footer>
        </body>
    </html>
    """
    
    result = extract_text_from_html(test_html)
    
    assert "Заголовок" in result
    assert "Основной текст" in result
    assert "Футер" not in result  # Должен быть удален
    assert "alert" not in result  # Скрипт должен быть удален

def test_chunking():
    """Тест разбиения текста на чанки."""
    text = "Это длинный текст, который должен быть разбит на несколько чанков для обработки."
    
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    
    assert len(chunks) > 1
    assert all(len(chunk) <= 20 for chunk in chunks)
    # Проверяем что есть перекрытие между чанками
    assert chunks[0][-5:] in chunks[1]  # Последние 5 символов первого чанка должны быть в начале второго

def test_response_formatting():
    """Тест форматирования ответа с ссылками."""
    answer = "Мы разработали систему для Lamoda [1] и KazanExpress [2]"
    sources = [
        "https://eora.ru/cases/lamoda",
        "https://eora.ru/cases/kazanexpress"
    ]
    
    formatted = add_html_links(answer, sources)
    
    assert "href=\"https://eora.ru/cases/lamoda\">[1]</a>" in formatted
    assert "href=\"https://eora.ru/cases/kazanexpress\">[2]</a>" in formatted

@pytest.mark.asyncio
async def test_hallucination_detection():
    """Тест детекции галлюцинаций."""
    from src.bot import detect_hallucinations
    
    # Тест на неопределенность
    answer = "Я не уверен, но возможно это связано с AI"
    context = "Мы разрабатываем системы искусственного интеллекта"
    
    result = await detect_hallucinations(answer, context)
    assert result == True
    
    # Тест на релевантный ответ
    answer = "Мы разрабатываем AI системы для e-commerce"
    context = "Мы разрабатываем AI системы для e-commerce. Искусственный интеллект e-commerce ритейл автоматизация"
    
    result = await detect_hallucinations(answer, context)
    assert result == False
    
    # Тест на ответ со ссылками (должен пройти)
    answer = "Мы разработали систему для Lamoda [1] и KazanExpress [2]"
    context = "Разработка систем для Lamoda и KazanExpress. EORA создала решения для ритейла."
    
    result = await detect_hallucinations(answer, context)
    assert result == False
    
    # Тест на общий ответ без ссылок
    answer = "Мы занимаемся разработкой искусственного интеллекта"
    context = "EORA разрабатывает системы искусственного интеллекта для различных отраслей"
    
    result = await detect_hallucinations(answer, context)
    assert result == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])