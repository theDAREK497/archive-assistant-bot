import re
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"

def extract_text_from_html(html_content: str) -> str:
    """Извлекает чистый текст из HTML, удаляя лишнее."""
    soup = BeautifulSoup(html_content, "lxml")

    # Убираем скрипты, стили и скрытые элементы
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    # Попробуем взять только контент
    main_content = soup.find("main") or soup.find("article") or soup.body
    if not main_content:
        return ""

    text = main_content.get_text(separator="\n", strip=True)
    # Убираем лишние пробелы
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()

def process_all_html():
    for html_file in BASE_DIR.glob("*.html"):
        html_content = html_file.read_text(encoding="utf-8")
        text = extract_text_from_html(html_content)
        txt_path = html_file.with_suffix(".txt")
        txt_path.write_text(text, encoding="utf-8")
        print(f"[PARSE] {html_file.name} -> {txt_path.name}")

if __name__ == "__main__":
    process_all_html()
