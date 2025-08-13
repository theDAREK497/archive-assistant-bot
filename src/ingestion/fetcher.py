import os
import httpx
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"
BASE_DIR.mkdir(parents=True, exist_ok=True)

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
    except Exception as e:
        print(f"[ERROR] {url} -> {e}")

def main():
    with open("sources.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        fetch_and_save(url)

if __name__ == "__main__":
    main()
