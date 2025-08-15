import os
import pickle
import faiss
import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
from src.embeddings.provider import get_embeddings

INDEX_PATH = Path("src/storage/index.faiss")
META_PATH = Path("src/storage/meta.pkl")
BATCH_SIZE = 32  # Оптимальный размер батча

def build_index(chunks_dir="src/storage/files/chunks"):
    print("[INDEX] Building FAISS index...")
    vectors = []
    metadata = []

    chunk_dir = Path(chunks_dir)
    files = list(chunk_dir.glob("*.txt"))
    if not files:
        print("[INDEX] No chunks found.")
        return

    # Загружаем маппинг URL
    url_mapping = {}
    mapping_file = Path("src/storage/files/url_mapping.json")
    if mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            try:
                url_mapping = json.load(f)
            except json.JSONDecodeError:
                print("Warning: Invalid JSON format in url_mapping.json. Using empty mapping.")
                url_mapping = {}

    # Сбор текстов и метаданных
    texts = []
    for file_path in tqdm(files, desc="Processing chunks"):
        text = file_path.read_text(encoding="utf-8")
        texts.append(text)
        
        # Извлекаем исходное имя файла
        if "_chunk" in file_path.stem:
            original_filename = file_path.stem.rsplit("_chunk", 1)[0] + ".html"
        else:
            original_filename = file_path.stem + ".html"
            
        # Получаем URL из маппинга (с поддержкой старого формата)
        url_entry = url_mapping.get(original_filename)
        final_url = "unknown_url"
        
        if isinstance(url_entry, dict):
            # Новый формат: {"original_url": "...", "final_url": "..."}
            final_url = url_entry.get("final_url", "unknown_url")
        elif isinstance(url_entry, str):
            # Старый формат: просто URL строка
            final_url = url_entry
        
        metadata.append({
            "file": file_path.name,
            "text": text,
            "url": final_url
        })

    if not texts:
        print("[INDEX] No texts to process")
        return

    # Обработка батчами
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding"):
        batch = texts[i:i+BATCH_SIZE]
        batch_embs = get_embeddings(batch)
        if batch_embs:
            vectors.extend(batch_embs)

    if not vectors:
        print("[INDEX] No embeddings generated.")
        return

    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors).astype("float32"))

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"[INDEX] Saved {len(vectors)} vectors.")

def search(query: str, top_k=4):
    if not INDEX_PATH.exists() or not META_PATH.exists():
        print("[SEARCH] No index found. Please build index first.")
        return []

    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    query_emb = get_embeddings([query])
    if not query_emb:
        return []

    D, I = index.search(np.array(query_emb).astype("float32"), top_k)
    return [metadata[idx] for idx in I[0]]

if __name__ == "__main__":
    build_index()
    print(search("Что вы можете сделать для ритейлеров?"))