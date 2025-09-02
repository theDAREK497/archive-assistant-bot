import re
from bs4 import BeautifulSoup, Comment
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"

def extract_text_from_html(html_content: str) -> str:
    """Извлекает чистый текст из HTML с улучшенной очисткой контента."""
    soup = BeautifulSoup(html_content, "lxml")
    
    # Удаляем ненужные элементы
    for tag in soup(["script", "style", "noscript", "header", "footer", 
                   "nav", "aside", "form", "button", "input", "select"]):
        tag.decompose()
        
    # Удаляем комментарии
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    # Удаляем элементы с классами/ids, содержащими запрещенные слова
    blacklist = ["advertisement", "ad", "popup", "modal", "cookie", "banner"]
    for tag in soup.find_all(True):
        classes = tag.get("class", []) or []
        id_val = tag.get("id", "") or ""
        
        if (any(black_word in " ".join(classes).lower() for black_word in blacklist) or
            any(black_word in id_val.lower() for black_word in blacklist)):
            tag.decompose()
            continue
            
        # Удаляем пустые элементы
        if not tag.get_text().strip():
            tag.decompose()

    # Ищем основной контент
    main_selectors = [
        {"name": "main"},
        {"name": "article"},
        {"name": "div", "class": "content"},
        {"name": "div", "class": "main"},
        {"name": "div", "class": "post"},
        {"name": "div", "class": "article"},
        {"name": "body"}
    ]
    
    main_content = None
    for selector in main_selectors:
        main_content = soup.find(**selector)
        if main_content:
            break

    if not main_content:
        return ""

    # Извлекаем текст с сохранением структуры
    text = main_content.get_text(separator="\n", strip=True)
    
    # Очищаем текст
    text = re.sub(r'\n\s*\n', '\n', text)  # Убираем множественные переносы
    text = re.sub(r'[ \t]+', ' ', text)    # Убираем лишние пробелы
    text = re.sub(r'\n\s+', '\n', text)    # Убираем пробелы в начале строк
    
    return text.strip()

def validate_parsing():
    """Валидация качества парсинга для основных страниц."""
    test_files = list(BASE_DIR.glob("*.html"))[:3]  # Проверяем первые 3 файла
    
    for html_file in test_files:
        html_content = html_file.read_text(encoding="utf-8")
        text = extract_text_from_html(html_content)
        
        # Проверяем качество извлечения текста
        if len(text) < 100:  # Слишком короткий текст
            print(f"⚠️  Предупреждение: {html_file.name} содержит мало текста ({len(text)} символов)")
        elif "html" in text.lower() or "body" in text.lower():
            print(f"⚠️  Предупреждение: {html_file.name} возможно содержит неочищенный HTML")

def process_all_html():
    """Обрабатывает все HTML файлы с валидацией."""
    for html_file in BASE_DIR.glob("*.html"):
        try:
            html_content = html_file.read_text(encoding="utf-8")
            text = extract_text_from_html(html_content)
            
            txt_path = html_file.with_suffix(".txt")
            txt_path.write_text(text, encoding="utf-8")
            print(f"[PARSE] {html_file.name} -> {txt_path.name} ({len(text)} символов)")
            
        except Exception as e:
            print(f"[ERROR] Ошибка обработки {html_file.name}: {str(e)}")

if __name__ == "__main__":
    print("Запуск улучшенного парсера...")
    process_all_html()
    print("\nВалидация качества парсинга:")
    validate_parsing()