import os
import httpx
import json
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"
BASE_DIR.mkdir(parents=True, exist_ok=True)
URL_MAPPING_FILE = BASE_DIR / "url_mapping.json"

def slugify_url(url: str) -> str:
    """Преобразует URL в безопасное имя файла."""
    parsed = urlparse(url)
    safe_path = parsed.netloc + parsed.path
    safe_path = safe_path.replace("/", "_").replace("?", "_")
    return safe_path.strip("_")

def fetch_and_save(url: str):
    """Скачивает HTML страницы и сохраняет локально."""
    print(f"[FETCH] {url}")
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True)
        r.raise_for_status()

        final_url = str(r.url)
        if final_url != url:
            print(f"[REDIRECT] {url} -> {final_url}")

        filename = slugify_url(final_url) + ".html"
        filepath = BASE_DIR / filename

        filepath.write_text(r.text, encoding="utf-8")
        print(f"[OK] Saved to {filepath}")

        # Обновляем маппинг URL
        url_mapping = {}
        if URL_MAPPING_FILE.exists():
            with open(URL_MAPPING_FILE, "r", encoding="utf-8") as f:
                url_mapping = json.load(f)
        
        url_mapping[filename] = final_url
        
        with open(URL_MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(url_mapping, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"[ERROR] {url} -> {e}")

def main():
    # Загружаем существующий маппинг
    url_mapping = {}
    if URL_MAPPING_FILE.exists():
        with open(URL_MAPPING_FILE, "r", encoding="utf-8") as f:
            url_mapping = json.load(f)
    
    with open("sources.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Фильтруем уже скачанные URL
    new_urls = [url for url in urls if slugify_url(url) + ".html" not in url_mapping]
    
    for url in new_urls:
        fetch_and_save(url)

if __name__ == "__main__":
    main()