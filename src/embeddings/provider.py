import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL")

def get_embedding(text: str):
    """
    Получает embedding для текста через LM Studio API.
    """
    url = f"{BASE_URL}/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "input": text
    }
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]
    except Exception as e:
        print(f"[EMBED ERROR] {e}")
        return None

if __name__ == "__main__":
    emb = get_embedding("Привет, мир!")
    print(len(emb), "dims")
