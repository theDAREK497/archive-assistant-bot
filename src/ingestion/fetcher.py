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
SSL_VERIFY = os.getenv("SSL_VERIFY", "false").lower() == "true"

def slugify_url(url: str) -> str:
    """
    Преобразует URL в безопасное имя файла
    
    Args:
        url: URL для преобразования
        
    Returns:
        Безопасное имя файла
    """
    parsed = urlparse(url)
    safe_path = parsed.netloc + parsed.path
    return safe_path.replace("/", "_").replace("?", "_").strip("_")

def fetch_and_save(url: str):
    """
    Скачивает HTML страницы и сохраняет локально
    
    Args:
        url: URL для скачивания
    """
    print(f"[FETCH] {url}")
    try:
        # Загрузка с учетом SSL_VERIFY
        r = httpx.get(
            url, 
            timeout=15, 
            follow_redirects=True,
            verify=SSL_VERIFY
        )
        r.raise_for_status()

        final_url = str(r.url)  # Конечный URL после редиректов
        filename = slugify_url(final_url) + ".html"
        filepath = BASE_DIR / filename

        # Сохранение файла
        filepath.write_text(r.text, encoding="utf-8")
        print(f"[OK] Saved to {filepath}")

        # Обновление маппинга URL
        url_mapping = {}
        if URL_MAPPING_FILE.exists():
            try:
                with open(URL_MAPPING_FILE, "r", encoding="utf-8") as f:
                    url_mapping = json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Invalid JSON in url_mapping, resetting")
        
        # Сохраняем оба URL (оригинальный и конечный)
        url_mapping[filename] = {
            "original_url": url,
            "final_url": final_url
        }
        
        with open(URL_MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(url_mapping, f, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        print(f"[HTTP ERROR] {url} -> {str(e)}")
    except Exception as e:
        print(f"[ERROR] {url} -> {str(e)}")

def main():
    """Основная функция обработки URL"""
    # Загрузка существующего маппинга
    url_mapping = {}
    if URL_MAPPING_FILE.exists():
        try:
            with open(URL_MAPPING_FILE, "r", encoding="utf-8") as f:
                url_mapping = json.load(f)
        except json.JSONDecodeError:
            print("[ERROR] Corrupted url_mapping.json, resetting")
            url_mapping = {}
    
    # Загрузка URL из файла
    with open("sources.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Фильтрация уже обработанных URL
    new_urls = [
        url for url in urls 
        if not any(slugify_url(url) in key for key in url_mapping)
    ]
    
    # Обработка новых URL
    for url in new_urls:
        fetch_and_save(url)

if __name__ == "__main__":
    main()