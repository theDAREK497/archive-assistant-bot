import os
import requests
from typing import List
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Получает embeddings для батча текстов"""
    url = f"{BASE_URL}/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "input": texts
    }
    
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return [item["embedding"] for item in r.json()["data"]]
    except Exception as e:
        print(f"[EMBED ERROR] {str(e)}")
        return []